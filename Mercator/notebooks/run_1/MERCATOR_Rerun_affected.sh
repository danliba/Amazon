#!/bin/bash
#SBATCH --job-name=MERCATOR_rerun_badW
#SBATCH --ntasks=8
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=8
#SBATCH --mem=250G
#SBATCH --exclusive
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=logs/rerun_%j.out
#SBATCH --error=logs/rerun_%j.err

# Re-runs every deployment whose 185-day window touched the broken W data
# (all of 2004, and 2013-10). The job list is rerun_jobs.txt: "<seed> <offset> <date>".
#
# Unlike MERCATOR_Run_parcels_*.sh, this passes rdm_seed to papermill explicitly,
# so each release is reproduced with the same particle start positions as the
# original run and lands back in its own data/tracks_<seed>/ folder.
#
# Run Move_affected_tracks.sh FIRST -- parcels will not overwrite an existing zarr.

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

cd /work/bk1450/b383184/Amazon/Mercator/notebooks
mkdir -p logs executed_rerun

JOBS_FILE="${1:-rerun_jobs.txt}"

num_particles=10000
run_time_days=185
ref_date="1993-01-01"

mapfile -t jobs < <(grep -v '^[[:space:]]*$' "$JOBS_FILE")
echo "Loaded ${#jobs[@]} runs from ${JOBS_FILE}, distributing over ${SLURM_NTASKS} tasks"

for i in $(seq 0 $((SLURM_NTASKS - 1))); do
  my_jobs=()
  for idx in "${!jobs[@]}"; do
    if (( idx % SLURM_NTASKS == i )); then
      # keep only "<seed> <offset>", drop the human-readable date column
      my_jobs+=("$(echo "${jobs[$idx]}" | awk '{print $1, $2}')")
    fi
  done

  echo "Task ${i}: ${#my_jobs[@]} runs"

  printf '%s\n' "${my_jobs[@]}" | \
    srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 \
      xargs -n2 -P"${PAR:-8}" bash -c '
        seed=$0
        offset=$1
        papermill MERCATOR_parcels_TS.ipynb \
          "executed_rerun/MERCATOR_parcels_TS.seed${seed}.offset${offset}.ipynb" \
          -k python \
          -p offset "${offset}" \
          -p rdm_seed "${seed}" \
          -p ref_date "'"$ref_date"'" \
          -p num_particles "'"$num_particles"'" \
          -p run_time_days "'"$run_time_days"'" \
          || echo "FAILED seed=${seed} offset=${offset}"
      ' &
done

wait
echo "All tasks completed"
