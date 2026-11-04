#!/bin/bash
#SBATCH --job-name=kmeans_radius
#SBATCH --ntasks=1
#SBATCH --nodes=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=250G
#SBATCH --time=04:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=executed/kmeans_radius_%j.log

# ---------------------------------------------------------------------------
# Run stages of the run_2 RADIUS k-means pipeline via papermill, in order.
# Choose the stages with STAGES (default: Stage 1 only):
#
#   sbatch submit_clustering.sh                                  # 00 + 01
#   sbatch --export=ALL,STAGES="02" submit_clustering.sh         # optional K sweep
#   (notebook 1.5 is done BY HAND: fit, assign letters, SAVE_MODEL = True,
#    paste GROUP_MAP / GROUP_NAMES / RADIUS_WEIGHTS into config.py)
#   sbatch --export=ALL,STAGES="03 04" submit_clustering.sh      # after 1.5
#
# `set -e` stops the job if any stage fails, so a failed stage never feeds
# the next one.
# ---------------------------------------------------------------------------

set -eo pipefail

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
set -u

cd /work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/kmeans_radius/notebooks
mkdir -p executed

export MPLBACKEND=Agg
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-32}

# --- choices (edit these) ---------------------------------------------------
STAGES=${STAGES:-"00 01"}
BEST_K=70                    # the K saved by notebook 1.5
LABEL_COL=cluster_group      # "cluster_group" (merged) or "cluster_label" (raw)

run() {  # run <input.ipynb> [papermill -p args...]
  local nb="$1"; shift
  echo "=== $(date '+%F %T')  running ${nb} ==="
  papermill "${nb}" "executed/${nb%.ipynb}.executed.ipynb" \
    --log-output --no-progress-bar "$@"
}

for s in ${STAGES}; do
  case "${s}" in
    00) run 00_radius_choice.ipynb ;;
    01) run 01_extract_features.ipynb ;;
    02) run 02_kmeans_subsample.ipynb ;;
    03) run 03_assign_labels.ipynb -p BEST_K "${BEST_K}" ;;
    04) run 04_diagnostics.ipynb   -p BEST_K "${BEST_K}" -p LABEL_COL "${LABEL_COL}" ;;
    *)  echo "unknown stage ${s}"; exit 1 ;;
  esac
done

echo "=== $(date '+%F %T')  stages ${STAGES} complete ==="
