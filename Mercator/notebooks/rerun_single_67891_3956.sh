#!/bin/bash
#SBATCH --job-name=rerun_67891_3956
#SBATCH --ntasks=1
#SBATCH --nodes=1
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=logs/rerun_single_%j.out
#SBATCH --error=logs/rerun_single_%j.err

# Redo the one run lost to the parcels /tmp compile race in job 26244626.

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

cd /work/bk1450/b383184/Amazon/Mercator/notebooks
export TMPDIR=$(mktemp -d)   # private tmp: avoids the shared-kernel compile race

papermill MERCATOR_parcels_TS.ipynb \
  "executed_rerun/MERCATOR_parcels_TS.seed67891.offset3956.ipynb" \
  -k python \
  -p offset 3956 \
  -p rdm_seed 67891 \
  -p ref_date "1993-01-01" \
  -p num_particles 10000 \
  -p run_time_days 185 \
  || echo "FAILED seed=67891 offset=3956"
