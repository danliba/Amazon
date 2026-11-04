#!/bin/bash
#SBATCH --job-name=MERCATOR_parcels_v3
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=250G
#SBATCH --time=04:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
export OMP_NUM_THREADS=1

# usage:  sbatch v1.Run_parcels_UVW.sh <chunk_id>                 # 0-3: 1993-1994 (offsets 5-730, 37 per chunk), seed 11098723
#         sbatch v1.Run_parcels_UVW.sh <first> <last> [seed]     # offsets first, first+5, ..., last
# seed = rdm_seed of the notebook (default 11098723). Tracks go to tracks_v3_<seed>/.
mkdir -p executed
seed=11098723
if [ $# -ge 2 ]; then
  chunk=($(seq $1 5 $2))
  seed=${3:-$seed}
  echo "offsets ${chunk[0]}-${chunk[-1]} (${#chunk[@]} notebooks), seed ${seed}"
else
  chunk_id=$1                                     # 0, 1, 2 or 3
  offsets=($(seq 5 5 730))                        # 146 releases
  per=37
  chunk=("${offsets[@]:$((chunk_id * per)):$per}")
  echo "chunk ${chunk_id}: offsets ${chunk[0]}-${chunk[-1]}, seed ${seed}"
fi

printf '%s\n' "${chunk[@]}" | xargs -P19 -I{} \
  papermill v3.Run_parcels_UVW_adaptive.ipynb executed/v3.Run_parcels_UVW_adaptive.seed${seed}.offset{}.ipynb \
    -k python -p offset {} -p ref_date 1993-01-01 -p rdm_seed ${seed} \
    -p num_particles 16400 -p run_time_days 185
