#!/bin/bash
#SBATCH --job-name=v4_regroup
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=250G
#SBATCH --time=01:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=/work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/analysis/particle_diagnostics/v4.slurm-%j.out

# Regroup all 1534 run_2 v3 stores by the month each particle first reaches
# 1.5N ... 12N (crossing-date seasonality); counts all positions since release.
# Writes v4.hist_threshold_month.nc, v4.regroup_store_log.csv,
# figures/v4.regroup_<thr>N.png and executed/v4.Regroup_particles.out.ipynb
#
# Submit from particle_diagnostics:  sbatch v4.Regroup_particles.sh

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
export OMP_NUM_THREADS=1

cd /work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/analysis/particle_diagnostics
mkdir -p executed figures

papermill v4.Regroup_particles.ipynb executed/v4.Regroup_particles.out.ipynb \
  -k python --log-output -p n_workers 48
echo "=== v4 regroup notebook rc=$? ==="
