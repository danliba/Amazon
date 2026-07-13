#!/bin/bash
#SBATCH --job-name=kmeans_plume_234
#SBATCH --ntasks=1
#SBATCH --nodes=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=250G
#SBATCH --time=04:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=executed/kmeans_%j.log

# ---------------------------------------------------------------------------
# Run Stages 2 -> 3 -> 4 of the plume k-means pipeline, in order, via papermill.
# These notebooks are SEQUENTIAL and dependent (unlike the per-offset Parcels
# runs which were embarrassingly parallel):
#   02  fits MiniBatchKMeans for every k and pickles the models
#   03  assigns labels to all ~16.3M trajectories using model k=BEST_K
#   04  produces the diagnostic figures / summary table
# `set -e` stops the job if any stage fails, so a bad 02 never feeds 03.
# Stage 01 (feature extraction) must be run FIRST (notebook 01): this project
# samples three days (50/100/150), so its features.parquet differs from the
# sibling 50/100-day projects and cannot be reused. Stage 02 fits the shared
# StandardScaler + k-means in the standardized feature space.
# ---------------------------------------------------------------------------

set -eo pipefail

# conda's activate.d scripts (binutils: ADDR2LINE) are not `set -u`-safe, so
# enable nounset only *after* the environment is active.
module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
set -u

# --- run from the notebooks directory so `import config, pipeline` (which the
# notebooks resolve via "..") points at the project root --------------------
cd /work/bk1450/b383184/Amazon/Mercator/notebooks/Analysis/kmeans_analysis/kmean_analysis_30_180_stdZ_w/notebooks
mkdir -p executed

# headless plotting + match threads to the allocation
export MPLBACKEND=Agg
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-32}

# --- choices (edit these) ---------------------------------------------------
BEST_K=50                    # k carried into stages 3 & 4 (inspect 02 first)
LABEL_COL=cluster_group      # "cluster_group" (merged) or "cluster_label" (raw)

run() {  # run <input.ipynb> [papermill -p args...]
  local nb="$1"; shift
  echo "=== $(date '+%F %T')  running ${nb} ==="
  papermill "${nb}" "executed/${nb%.ipynb}.executed.ipynb" \
    --log-output --no-progress-bar "$@"
}

# Stage 2: fit + evaluate all k, pickle models (no parameters needed)
# run 02_kmeans_subsample.ipynb

# Stage 3: assign labels to every trajectory with the chosen k
run 03_assign_labels.ipynb -p BEST_K "${BEST_K}"

# Stage 4: diagnostics & figures at the chosen label level
run 04_diagnostics.ipynb  -p BEST_K "${BEST_K}" -p LABEL_COL "${LABEL_COL}"

echo "=== $(date '+%F %T')  all stages complete ==="
