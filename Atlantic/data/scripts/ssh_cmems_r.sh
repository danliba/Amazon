#!/bin/bash
#SBATCH --job-name=ssh_download
#SBATCH --ntasks=8
#SBATCH --ntasks-per-node=2
#SBATCH --nodes=4
#SBATCH --mem=50G
#SBATCH --cpus-per-task=4
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=logs/download_ssh_%j.out
#SBATCH --error=logs/download_ssh_%j.err

module load python3/2023.01-gcc-11.2.0

# Activate your environment if needed
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
# source /path/to/your/envs/bin/activate

python3 ssh_month.py 