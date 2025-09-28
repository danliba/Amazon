#!/bin/bash
#SBATCH --job-name=particles_array
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=1
#SBATCH --mem=0
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=logs/Particles_%A_%a.log
#SBATCH --error=logs/Particles_%A_%a.err

module load python3/2023.01-gcc-11.2.0

# Activate your environment if needed
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
# source /path/to/your/envs/bin/activate

# dates=("2022-06-01" "2022-07-01" "2022-08-01" "2022-09-01" "2022-10-01" "2022-11-01" "2022-12-01")
seq -w 1 12 | xargs -n 1 -P 6 -I{} python3 Particles_release.py "2022-{}-01"

# dates=("2023-01-01" "2023-02-01" "2023-03-01" "2023-04-01" "2023-05-01" "2023-06-01")

# python3 Particles_release.py ${dates[$SLURM_ARRAY_TASK_ID]}
