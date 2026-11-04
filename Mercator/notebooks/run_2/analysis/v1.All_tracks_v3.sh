#!/bin/bash
#SBATCH --job-name=MERCATOR_v3_bins
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=250G
#SBATCH --time=04:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=slurm-%j.out

# Spatial-bin ("bin analysis") products for the 1993-2013 production run,
# all four seeds (1534 zarr stores) combined into one climatology.
# Writes _hist_month_v3.nc, _hist_season_v3.nc, _hist_year_month_v3.nc,
# _hist_age_month_v3.nc and _store_log_v3.csv into this folder, plus the
# executed notebook executed/v1.All_tracks_v3.out.ipynb
#
# Submit from run_2/analysis:  sbatch v1.All_tracks_v3.sh

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
export OMP_NUM_THREADS=1

cd /work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/analysis
mkdir -p executed figures

papermill v1.All_tracks_v3.ipynb executed/v1.All_tracks_v3.out.ipynb \
  -k python --log-output -p n_workers 48
