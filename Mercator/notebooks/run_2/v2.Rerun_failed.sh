#!/bin/bash
#SBATCH --job-name=MERCATOR_rerun_v2
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=250G
#SBATCH --time=04:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450

# Reruns the 10 releases that did not finish in the v1 adaptive runs (jobs 27510599-27515056),
# now with v2.Run_parcels_UVW_adaptive.ipynb (29.8N cut-off + previous-month file fix).
#   timed out at 4 h : 360 370 455 470 475 480 490 495
#   Jan-1 00:00 start (TimeExtrapolationError): 365 730
# Their partial zarrs in tracks_adaptive_11098723/ are overwritten (parcels writes with mode="w").
# rdm_seed is passed explicitly: the v2 notebook default is 20, but these runs must reuse the
# seed of the other 136 releases (same start positions, same tracks folder).
#
# Submit from run_2:  sbatch v2.Rerun_failed.sh

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
export OMP_NUM_THREADS=1

mkdir -p executed
offsets=(360 365 370 455 470 475 480 490 495 730)
echo "rerun v2: offsets ${offsets[*]}"

printf '%s\n' "${offsets[@]}" | xargs -P10 -I{} \
  papermill v2.Run_parcels_UVW_adaptive.ipynb executed/v2.Run_parcels_UVW_adaptive.offset{}.ipynb \
    -k python -p offset {} -p ref_date 1993-01-01 -p rdm_seed 11098723 \
    -p num_particles 10000 -p run_time_days 185
