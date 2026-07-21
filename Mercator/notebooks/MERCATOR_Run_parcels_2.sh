#!/bin/bash
#SBATCH --job-name=MERCATOR_parcels_1993-1994
#SBATCH --ntasks=8
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=8
#SBATCH --mem=250G
#SBATCH --exclusive
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450

module load python3/2023.01-gcc-11.2.0

source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

num_particles=10000
run_time_days=185
ref_date="1993-01-01"

# Create executed directory
mkdir -p executed

# 8 chunks covering days 5-730 (1993-1994)
# Chunk 1: days 5-95
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 5 5 95 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 2: days 100-185
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 100 5 185 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 3: days 190-275
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 190 5 275 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 4: days 280-365
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 280 5 365 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 5: days 370-460 (1994)
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 370 5 460 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 6: days 465-555
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 465 5 555 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 7: days 560-650
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 560 5 650 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 8: days 655-730 (ends Dec 31, 1994)
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 655 5 730 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

wait