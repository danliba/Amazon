#!/bin/bash
#SBATCH --job-name=W_donwload
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=1
#SBATCH --mem=200G
#SBATCH --cpus-per-task=64
#SBATCH --time=08:00:00
#SBATCH --array=0-3
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=logs/download_W_%A_%a.out
#SBATCH --error=logs/download_W_%A_%a.err

# Define years to download
YEARS=(2023 2024 2025)
YEAR=${YEARS[$SLURM_ARRAY_TASK_ID]}

module load python3/2023.01-gcc-11.2.0

# Activate your environment if needed
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
# source /path/to/your/envs/bin/activate

echo "Downloading year $YEAR..."
python3 W_hpc.py $YEAR
