#!/bin/bash
#SBATCH --job-name=V_donwload
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=1
#SBATCH --mem=60G
#SBATCH --cpus-per-task=64
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=logs/download_V_%A_%a.out
#SBATCH --error=logs/download_V_%A_%a.err

# Define years to download
YEARS=(2022 2023 2024 2025)
YEAR=${YEARS[$SLURM_ARRAY_TASK_ID]}

module load python3/2023.01-gcc-11.2.0

# Activate your environment if needed
# source /path/to/your/envs/bin/activate

echo "Downloading year $YEAR..."
python V_hpc.py $YEAR
