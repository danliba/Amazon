#!/bin/bash
#SBATCH --job-name=V_${YEAR}
#SBATCH --array=1-12
#SBATCH --ntasks=1
#SBATCH --mem=6G
#SBATCH --cpus-per-task=1
#SBATCH --time=02:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=logs/V_%x_%A_%a.out
#SBATCH --error=logs/V_%x_%A_%a.err

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

echo "Downloading V for year=$YEAR month=$SLURM_ARRAY_TASK_ID"
python3 V_HPC.py $YEAR $SLURM_ARRAY_TASK_ID