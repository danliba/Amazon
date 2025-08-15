#!/bin/bash
#SBATCH --job-name=Atlantic_parcels_2
#SBATCH --ntasks=4  #  
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

# run 185 day batches on each of the four tasks
num_particles=10000
run_time_days=185

year=2022
min_doy=155
max_doy=365
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "seq -w $min_doy 5 $max_doy | xargs -n1 -P12 -I{} papermill Atlantic_parcels_3.ipynb executed/Atlantic_parcels_3.y${year}-doy{}.ipynb -k python -p start_year $year -p start_day_of_year {} -p num_particles $num_particles -p run_time_days $run_time_days" & 

year=2023
min_doy=0
max_doy=365
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "seq -w $min_doy 5 $max_doy | xargs -n1 -P12 -I{} papermill Atlantic_parcels_3.ipynb executed/Atlantic_parcels_3.y${year}-doy{}.ipynb -k python -p start_year $year -p start_day_of_year {} -p num_particles $num_particles -p run_time_days $run_time_days" & 

year=2024
min_doy=0
max_doy=365
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "seq -w $min_doy 5 $max_doy | xargs -n1 -P12 -I{} papermill Atlantic_parcels_3.ipynb executed/Atlantic_parcels_3.y${year}-doy{}.ipynb -k python -p start_year $year -p start_day_of_year {} -p num_particles $num_particles -p run_time_days $run_time_days" & 

year=2025
min_doy=0
max_doy=155
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "seq -w $min_doy 5 $max_doy | xargs -n1 -P12 -I{} papermill Atlantic_parcels_3.ipynb executed/Atlantic_parcels_3.y${year}-doy{}.ipynb -k python -p start_year $year -p start_day_of_year {} -p num_particles $num_particles -p run_time_days $run_time_days" & 

wait 
