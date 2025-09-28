#!/bin/bash
#SBATCH --job-name=parcels
#SBATCH --ntasks=4  # one per 6 months
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=4
#SBATCH --mem=250G
#SBATCH --exclusive
#SBATCH --time=00:15:00
#SBATCH --partition=compute
#SBATCH --account=bk1450

module load python3/2023.01-gcc-11.2.0

# Activate your environment if needed
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
# source /path/to/your/envs/bin/activate

# run 6-month batches on each of the four tasks

srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "seq 1 6 | xargs -n1 -P6 -I{} python3 Particles_release.py \"2022-0{}-01\"" &

srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "seq -w 7 12 | xargs -n1 -P6 -I{} python3 Particles_release.py \"2022-{}-01\"" &

srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "seq 1 6 | xargs -n1 -P6 -I{} python3 Particles_release.py \"2023-0{}-01\"" &

srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "seq -w 7 12 | xargs -n1 -P6 -I{} python3 Particles_release.py \"2023-{}-01\"" &

wait 