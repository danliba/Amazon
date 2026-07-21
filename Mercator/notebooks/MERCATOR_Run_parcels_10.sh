#!/bin/bash
#SBATCH --job-name=MERCATOR_parcels_2009-2010
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

mkdir -p executed

# ============================================================
# 8 chunks covering days 5941–6736 (2009-04-13 to 2011-05-18)
# ============================================================

# Chunk 1: 5941–6036 (2009-04-13 to 2009-07-17)
# 5941 5946 5951 5956 5961 5966 5971 5976 5981 5986
# 5991 5996 6001 6006 6011 6016 6021 6026 6031 6036
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 5941 5 6036 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 2: 6041–6136 (2009-07-22 to 2009-10-25)
# 6041 6046 6051 6056 6061 6066 6071 6076 6081 6086
# 6091 6096 6101 6106 6111 6116 6121 6126 6131 6136
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 6041 5 6136 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 3: 6141–6236 (2009-10-30 to 2010-02-02)
# 6141 6146 6151 6156 6161 6166 6171 6176 6181 6186
# 6191 6196 6201 6206 6211 6216 6221 6226 6231 6236
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 6141 5 6236 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 4: 6241–6336 (2010-02-07 to 2010-05-13)
# 6241 6246 6251 6256 6261 6266 6271 6276 6281 6286
# 6291 6296 6301 6306 6311 6316 6321 6326 6331 6336
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 6241 5 6336 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 5: 6341–6436 (2010-05-18 to 2010-08-21)
# 6341 6346 6351 6356 6361 6366 6371 6376 6381 6386
# 6391 6396 6401 6406 6411 6416 6421 6426 6431 6436
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 6341 5 6436 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 6: 6441–6536 (2010-08-26 to 2010-11-29)
# 6441 6446 6451 6456 6461 6466 6471 6476 6481 6486
# 6491 6496 6501 6506 6511 6516 6521 6526 6531 6536
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 6441 5 6536 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 7: 6541–6636 (2010-12-04 to 2011-03-09)
# 6541 6546 6551 6556 6561 6566 6571 6576 6581 6586
# 6591 6596 6601 6606 6611 6616 6621 6626 6631 6636
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 6541 5 6636 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 8: 6641–6736 (2011-03-14 to 2011-06-12)
# 6641 6646 6651 6656 6661 6666 6671 6676 6681 6686
# 6691 6696 6701 6706 6711 6716 6721 6726 6731 6736
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 6641 5 6736 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

wait