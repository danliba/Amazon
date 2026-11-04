#!/bin/bash
#SBATCH --job-name=MERCATOR_rerun_v3
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=250G
#SBATCH --time=04:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450

# Reruns single releases of the v3 run (tracks_v3_11098723) with the same settings as v1.Run_parcels_UVW.sh.
#   400: kernel failed to start in job 27549554 (ZMQ port clash), no zarr written
# Pass the seed of the chunk the offsets belong to (see readme_Parcels_Release.m), so the start positions
# match the other releases of that seed and the zarr lands in tracks_v3_<seed>/.
#
# Submit from run_2:  sbatch v3.Rerun_offset.sh <seed> <offset> [<offset> ...]
#   e.g. sbatch v3.Rerun_offset.sh 11098723 400

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
export OMP_NUM_THREADS=1

mkdir -p executed
seed=$1; shift
offsets=("$@")
echo "rerun v3: seed ${seed}, offsets ${offsets[*]}"

printf '%s\n' "${offsets[@]}" | xargs -P19 -I{} \
  papermill v3.Run_parcels_UVW_adaptive.ipynb executed/v3.Run_parcels_UVW_adaptive.seed${seed}.offset{}.ipynb \
    -k python -p offset {} -p ref_date 1993-01-01 -p rdm_seed ${seed} \
    -p num_particles 16400 -p run_time_days 185
