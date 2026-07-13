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

# Run the SINGLE template notebook 1.Clusters_.ipynb once per k-means group,
# sequentially, passing the group in through the CLUSTER env var (cell 1 does
# os.environ.get("CLUSTER", "F")). This replaces the seven hardcoded
# 1.Clusters_<G>.ipynb copies: one notebook to edit, seven runs.
#
# Only one dask cluster is alive at a time, so memory is never oversubscribed.
#
# Submit all groups:      sbatch run_cluster_diag_template.sh
# Submit a subset:        sbatch run_cluster_diag_template.sh C E
# Run outside SLURM:      ./run_cluster_diag_template.sh F

set -eo pipefail

# NB: conda's activation hooks (e.g. activate-binutils_linux-64.sh) reference
# unset vars like $ADDR2LINE, so `set -u` must stay off until after activation.
module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

set -u                          # safe to be strict from here on

export MPLBACKEND=Agg           # no display on compute nodes

NBDIR=/work/bk1450/b383184/Amazon/Mercator/notebooks/Analysis/particle_diagnostics/clusters_diagnostics
cd "$NBDIR"
mkdir -p executed figures logs output

PAPERMILL=/work/bk1450/b383184/conda/envs/parcels_3.1.2/bin/papermill
TEMPLATE=1.Clusters_.ipynb

# groups from the command line, else all of them
if [ "$#" -gt 0 ]; then
  CLUSTERS=("$@")
else
  CLUSTERS=(A B1 B2 C D E F)    # NB: not GROUPS (reserved bash builtin)
fi

echo "[$(date)] template: $TEMPLATE"
echo "[$(date)] groups:   ${CLUSTERS[*]}"

failed=()
for CL in "${CLUSTERS[@]}"; do
  echo "[$(date)] === starting group $CL ==="

  # CLUSTER is read by cell 1 of the template. Exported per-iteration, so each
  # papermill run gets its own group and writes its own output/ and figures/.
  if CLUSTER="$CL" "$PAPERMILL" "$TEMPLATE" "executed/1.Clusters_${CL}.executed.ipynb" \
        -k parcels_3.1.2 --log-output; then
    echo "[$(date)] === finished group $CL ==="
  else
    # don't let one bad group kill the remaining six -- collect and report at the end
    echo "[$(date)] !!! group $CL FAILED (see executed/1.Clusters_${CL}.executed.ipynb) !!!"
    failed+=("$CL")
  fi
done

if [ "${#failed[@]}" -gt 0 ]; then
  echo "[$(date)] done, but these groups failed: ${failed[*]}"
  exit 1
fi

echo "[$(date)] all groups done"
