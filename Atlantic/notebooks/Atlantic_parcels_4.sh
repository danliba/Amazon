#!/bin/bash
#SBATCH --job-name=Atlantic_parcels_2
#SBATCH --ntasks=23
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=23
#SBATCH --mem=250G
#SBATCH --exclusive
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450

module load python3/2023.01-gcc-11.2.0

# Activate your environment if needed
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

# run 185 day batches on each of the eight tasks
num_particles=10000
run_time_days=185

ref_date="2022-01-01"

for offset in $(seq -w 155 50 1255); do  # make sure that num iters matches ntasks
    offset_end=$[offset + 45]
    srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "seq -w $offset 5 $offset_end | xargs -n1 -P5 -I{} papermill Atlantic_parcels_3.ipynb executed/Atlantic_parcels_3.y${ref_date}-offset-days${offset}.ipynb -k python -p offset {} -p ref_date ${ref_date} -p num_particles $num_particles -p run_time_days $run_time_days" & 
done

