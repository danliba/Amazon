#!/bin/bash
#SBATCH --job-name=cluster_diag
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=128
#SBATCH --mem=250G
#SBATCH --exclusive
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=logs/diag_%j.log
#SBATCH --error=logs/diag_%j.err

# Run the SINGLE template notebook 1.Clusters_.ipynb once per k-means group, several
# groups AT A TIME inside this one job (xargs -P), passing the group in through the
# CLUSTER env var -- cell 1 does os.environ.get("CLUSTER").
#
# Submit:  sbatch run_cluster_diag_parallel.sh
#
# ---------------------------------------------------------------------------------
# Why the groups are batched instead of all 7 at once: they are VERY uneven, and each
# notebook holds its own dask cluster inside this node's 250 GB.
#
#     E   8.01M particles   ~380 GB if held in memory   <- cannot be persisted at all
#     B1  2.23M             ~106 GB
#     A   2.13M             ~101 GB
#     D   2.00M              ~95 GB
#     B2  0.84M              ~40 GB
#     C   0.79M              ~38 GB
#     F   0.15M               ~7 GB
#
# The notebook persists only if the group fits its dask budget and otherwise streams
# from disk, so nothing here can OOM -- but the memory each concurrent notebook is
# ALLOWED to take (DASK_WORKERS x DASK_MEM_GB) must still sum to under 250 GB.
#
# WAVE 1: the six small/medium groups, 6-way parallel, 36 GB budget each = 216 GB.
#         A, B1 and D stream; B2, C and F persist.
# WAVE 2: E alone, with the whole node (streams, but gets all the cores and RAM).
# ---------------------------------------------------------------------------------

set -eo pipefail

# NB: conda's activation hooks (e.g. activate-binutils_linux-64.sh) reference
# unset vars like $ADDR2LINE, so `set -u` must stay off until after activation.
module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

set -u                          # safe to be strict from here on

export MPLBACKEND=Agg           # no display on compute nodes
export OMP_NUM_THREADS=1        # keep BLAS from fighting dask for the cores

NBDIR=/work/bk1450/b383184/Amazon/Mercator/notebooks/Analysis/particle_diagnostics/clusters_diagnostics
cd "$NBDIR"
mkdir -p executed figures logs output

PAPERMILL=/work/bk1450/b383184/conda/envs/parcels_3.1.2/bin/papermill
TEMPLATE=1.Clusters_.ipynb

# one group -> one papermill run. CLUSTER/DASK_* are read by cells 1 and 5.
run_group() {
  CL=$1
  echo "[$(date)] === starting $CL (workers=$DASK_WORKERS mem=${DASK_MEM_GB}G) ==="
  CLUSTER="$CL" "$PAPERMILL" "$TEMPLATE" "executed/1.Clusters_${CL}.executed.ipynb" \
      -k parcels_3.1.2 --log-output \
    && echo "[$(date)] === finished $CL ===" \
    || echo "[$(date)] !!! $CL FAILED -- see executed/1.Clusters_${CL}.executed.ipynb !!!"
}
export -f run_group
export PAPERMILL TEMPLATE

# ---- wave 1: the six that fit alongside each other, 6 at a time -------------------
export DASK_WORKERS=3
export DASK_THREADS=4           # 6 groups x 3 x 4 = 72 threads on 128 cores
export DASK_MEM_GB=12           # 6 x 3 x 12 = 216 GB ceiling, under the 250 G ask

echo "[$(date)] ### WAVE 1: A B1 B2 C D F (6-way parallel) ###"
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 128 /bin/bash -c -l '
  printf "%s\n" A B1 B2 C D F | xargs -n1 -P6 -I{} bash -c "run_group {}"
'

# ---- wave 2: E alone, whole node --------------------------------------------------
export DASK_WORKERS=8
export DASK_THREADS=4
export DASK_MEM_GB=28           # 8 x 28 = 224 GB; E streams rather than persists

echo "[$(date)] ### WAVE 2: E (alone, whole node) ###"
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 128 /bin/bash -c -l '
  run_group E
'

echo "[$(date)] all groups done"
grep -l "FAILED" logs/diag_${SLURM_JOB_ID:-}.log 2>/dev/null && echo "NB: some groups failed, see log above"
