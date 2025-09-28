#!/bin/bash
#SBATCH --job-name=particles_array
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=1
#SBATCH --mem=50G
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=logs/Animation2_%A_%a.log
#SBATCH --error=logs/Animation2_%A_%a.err

module load python3/2023.01-gcc-11.2.0

# Activate your environment if needed
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

# Create necessary directories
mkdir -p logs executed

papermill Animation_science_day.ipynb \
          executed/Animation_science_day_executed_2.ipynb


