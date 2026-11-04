#!/bin/bash
#SBATCH --job-name=radius_eval
#SBATCH --ntasks=1
#SBATCH --nodes=1
#SBATCH --cpus-per-task=128
#SBATCH --mem=250G
#SBATCH --time=04:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=eval_%j.log
# usage: sbatch run_eval.sh <configs.json> [n_jobs]
set -eo pipefail
module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
set -u
cd /work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/kmeans_radius/data/experiments
N_JOBS=${2:-16}
export OMP_NUM_THREADS=$(( SLURM_CPUS_PER_TASK / N_JOBS ))
python eval_configs.py "$1" "$N_JOBS"
