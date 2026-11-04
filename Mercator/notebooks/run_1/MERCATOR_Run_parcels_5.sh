#!/bin/bash
#SBATCH --job-name=MERCATOR_parcels_1999-2000
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

# 8 chunks covering days 2201-2926 (1999-01-05 to 2000-12-30)
# Chunk 1: 2201, 2206, 2211, 2216, 2221, 2226, 2231, 2236, 2241, 2246, 2251, 2256, 2261, 2266, 2271, 2276, 2281, 2286, 2291
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 2201 5 2291 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 2: 2296, 2301, 2306, 2311, 2316, 2321, 2326, 2331, 2336, 2341, 2346, 2351, 2356, 2361, 2366, 2371, 2376, 2381, 2386
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 2296 5 2386 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 3: 2391, 2396, 2401, 2406, 2411, 2416, 2421, 2426, 2431, 2436, 2441, 2446, 2451, 2456, 2461, 2466, 2471, 2476, 2481
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 2391 5 2481 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 4: 2486, 2491, 2496, 2501, 2506, 2511, 2516, 2521, 2526, 2531, 2536, 2541, 2546, 2551, 2556, 2561, 2566 (ends 1999)
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 2486 5 2566 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 5: 2571, 2576, 2581, 2586, 2591, 2596, 2601, 2606, 2611, 2616, 2621, 2626, 2631, 2636, 2641, 2646, 2651, 2656, 2661 (2000 - leap year)
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 2571 5 2661 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 6: 2666, 2671, 2676, 2681, 2686, 2691, 2696, 2701, 2706, 2711, 2716, 2721, 2726, 2731, 2736, 2741, 2746, 2751, 2756
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 2666 5 2756 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 7: 2761, 2766, 2771, 2776, 2781, 2786, 2791, 2796, 2801, 2806, 2811, 2816, 2821, 2826, 2831, 2836, 2841, 2846, 2851
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 2761 5 2851 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 8: 2856, 2861, 2866, 2871, 2876, 2881, 2886, 2891, 2896, 2901, 2906, 2911, 2916, 2921, 2926 (ends Dec 30, 2000)
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 2856 5 2926 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

wait