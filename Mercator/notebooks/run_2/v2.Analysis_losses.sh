#!/bin/bash
#SBATCH --job-name=MERCATOR_v5_losses
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=250G
#SBATCH --time=04:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450

# Runs v5.Meso_boundaries_bigrun_v3_losses.ipynb once per seed of the 1993-2013 production,
# the four in parallel on one node. Each writes
#   executed/v5.losses.seed<seed>.ipynb  and  tracks_v3_<seed>_boundary_losses.parquet
# The combined 1993-2013 numbers are then made by v6.Meso_boundaries_all_losses.ipynb.
#
# Submit from run_2:  sbatch v2.Analysis_losses.sh

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
export OMP_NUM_THREADS=1

mkdir -p executed
seeds=(11098723 45678 67891 78876)

printf '%s\n' "${seeds[@]}" | xargs -P4 -I{} \
  papermill v5.Meso_boundaries_bigrun_v3_losses.ipynb executed/v5.losses.seed{}.ipynb \
    -k python -p tracks_dir tracks_v3_{} -p out_table tracks_v3_{}_boundary_losses.parquet
