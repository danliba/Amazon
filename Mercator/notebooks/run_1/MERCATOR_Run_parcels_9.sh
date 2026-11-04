#!/bin/bash
#SBATCH --job-name=MERCATOR_parcels_2007-2008
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

#
# Chunk 1: 5141–5236 (2007-01-29 to 2007-05-04)
# 5141 5146 5151 5156 5161 5166 5171 5176 5181 5186
# 5191 5196 5201 5206 5211 5216 5221 5226 5231 5236
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 5141 5 5236 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 2: 5241–5336 (2007-05-09 to 2007-08-12)
# 5241 5246 5251 5256 5261 5266 5271 5276 5281 5286
# 5291 5296 5301 5306 5311 5316 5321 5326 5331 5336
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 5241 5 5336 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 3: 5341–5436 (2007-08-17 to 2007-11-20)
# 5341 5346 5351 5356 5361 5366 5371 5376 5381 5386
# 5391 5396 5401 5406 5411 5416 5421 5426 5431 5436
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 5341 5 5436 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 4: 5441–5536 (2007-11-25 to 2008-02-28)
# 5441 5446 5451 5456 5461 5466 5471 5476 5481 5486
# 5491 5496 5501 5506 5511 5516 5521 5526 5531 5536
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 5441 5 5536 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 5: 5541–5636 (2008-03-04 to 2008-06-07)
# 5541 5546 5551 5556 5561 5566 5571 5576 5581 5586
# 5591 5596 5601 5606 5611 5616 5621 5626 5631 5636
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 5541 5 5636 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 6: 5641–5736 (2008-06-12 to 2008-09-15)
# 5641 5646 5651 5656 5661 5666 5671 5676 5681 5686
# 5691 5696 5701 5706 5711 5716 5721 5726 5731 5736
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 5641 5 5736 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 7: 5741–5836 (2008-09-20 to 2008-12-24)
# 5741 5746 5751 5756 5761 5766 5771 5776 5781 5786
# 5791 5796 5801 5806 5811 5816 5821 5826 5831 5836
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 5741 5 5836 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 8: 5841–5936 (2008-12-29 to 2009-04-03)
# 5841 5846 5851 5856 5861 5866 5871 5876 5881 5886
# 5891 5896 5901 5906 5911 5916 5921 5926 5931 5936

srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"

  seq 5841 5 5936 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

wait