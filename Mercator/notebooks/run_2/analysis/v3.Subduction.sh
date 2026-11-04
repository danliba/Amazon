#!/bin/bash
#SBATCH --job-name=v3_subduction
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=250G
#SBATCH --time=04:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=/work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/analysis/v3.slurm-%j.out

# Subduction diagnostics over ALL 1534 stores of the 1993-2013 production run
# (tracks_v3_11098723 / _45678 / _67891 / _78876 -> one 21-year climatology).
# Writes v3.subduction_events_v3.parquet, v3.subduction_stores_v3.csv,
# v3.subduction_ageprofile_v3.npz and figures/v3.subduction_*.png, plus the
# executed notebook executed/v3.Subduction_v3.out.ipynb
#
# Reuses the shared bin edges v2.bins_v3.npz written by the v2 notebooks, so the
# subduction maps sit on the same grid as the count and monthly-mean maps.
#
# Submit from run_2/analysis:  sbatch v3.Subduction.sh

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
export OMP_NUM_THREADS=1

cd /work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/analysis
mkdir -p executed figures

papermill v3.Subduction_v3.ipynb executed/v3.Subduction_v3.out.ipynb \
  -k python --log-output -p n_jobs 48
echo "=== subduction notebook rc=$? ==="
