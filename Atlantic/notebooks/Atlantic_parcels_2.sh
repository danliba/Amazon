#!/bin/bash
#SBATCH --job-name=Atlantic_parcels_2
#SBATCH --ntasks=4  # one per 6 months
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=4
#SBATCH --mem=250G
#SBATCH --exclusive
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450

module load python3/2023.01-gcc-11.2.0

# Activate your environment if needed
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
# source /path/to/your/envs/bin/activate

# run 6-month batches on each of the four tasks
num_particles=100000
run_time_days=185

for year in {2022..2025}; do 

    srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "seq -w 1 12 | xargs -n1 -P6 -I{} papermill Atlantic_parcels_2.ipynb executed/Atlantic_parcels_2.${year}-{}-01.ipynb -k python -p start_time ${year}-{}-01T00:00:00 -p num_particles $num_particles -p run_time_days $run_time_days" & 
done
wait 
