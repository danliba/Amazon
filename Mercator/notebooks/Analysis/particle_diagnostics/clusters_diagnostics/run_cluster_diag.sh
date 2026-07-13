#!/bin/bash
#SBATCH --job-name=cluster_diag
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=250G
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=logs/diag_%j.log
#SBATCH --error=logs/diag_%j.err

# Run one dedicated notebook per k-means group, SEQUENTIALLY (one after the
# other) in a single task. Each group has its own notebook 1.Clusters_<G>.ipynb
# with the cluster hardcoded in cell 1; papermill executes them in turn. Only
# one dask cluster is alive at a time, so memory is never oversubscribed.
#
# Submit:  sbatch run_cluster_diag.sh

set -eo pipefail

# NB: conda's activation hooks (e.g. activate-binutils_linux-64.sh) reference
# unset vars like $ADDR2LINE, so `set -u` must stay off until after activation.
module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

set -u                          # safe to be strict from here on

export MPLBACKEND=Agg          # no display on compute nodes

NBDIR=/work/bk1450/b383184/Amazon/Mercator/notebooks/Analysis/particle_diagnostics/clusters_diagnostics
cd "$NBDIR"
mkdir -p executed figures logs

PAPERMILL=/work/bk1450/b383184/conda/envs/parcels_3.1.2/bin/papermill
CLUSTERS=(A B1 B2 C D E F)     # NB: not GROUPS (reserved bash builtin)

for CL in "${CLUSTERS[@]}"; do
  echo "[$(date)] === starting group $CL ==="
  "$PAPERMILL" "1.Clusters_${CL}.ipynb" "executed/1.Clusters_${CL}.executed.ipynb" \
      -k parcels_3.1.2 --log-output
  echo "[$(date)] === finished group $CL ==="
done

echo "[$(date)] all groups done"
