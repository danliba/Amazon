#!/bin/bash
#SBATCH --job-name=v2_monthly_means
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=250G
#SBATCH --time=04:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=/work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/analysis/v2.slurm-%j.out

# Monthly binned means over ALL 1534 stores of the 1993-2013 production run
# (tracks_v3_11098723 / _45678 / _67891 / _78876 -> one 21-year climatology).
#   1) v2.Monthly_means_z_temp_sal_v3.ipynb -> mean_{z,temp,sal}_month_v3.zarr (+ v2.bins_v3.npz)
#   2) v2.Buoyancy_sigma0_v3.ipynb          -> mean_{b,sigma0}_month_v3.zarr   (reuses the same bins)
# Run sequentially: (2) needs the bin edges written by (1).
#
# Submit from run_2/analysis:  sbatch v2.Monthly_means.sh

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
export OMP_NUM_THREADS=1

cd /work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/analysis
mkdir -p executed figures

papermill v2.Monthly_means_z_temp_sal_v3.ipynb executed/v2.Monthly_means_z_temp_sal_v3.ipynb \
  -k python -p n_jobs 32
rc1=$?
echo "=== z/temp/sal notebook rc=$rc1 ==="

papermill v2.Buoyancy_sigma0_v3.ipynb executed/v2.Buoyancy_sigma0_v3.ipynb \
  -k python -p n_jobs 32
rc2=$?
echo "=== buoyancy/sigma0 notebook rc=$rc2 ==="
exit $(( rc1 | rc2 ))
