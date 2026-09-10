#!/bin/bash
#SBATCH --job-name=UVW_CMEMS
#SBATCH --nodes=4
#SBATCH --ntasks=4
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=200G
#SBATCH --exclusive
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=logs/Wf_%j.out
#SBATCH --error=logs/Wf_%j.err

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

cd /work/bk1450/b383184/Amazon/Mercator/data
mkdir -p logs executed_W

OUT_DIR="/work/bk1450/b383184/Amazon/Mercator/data/variables_c/UVW"
W_IN_DIR="/work/bk1450/b383184/Amazon/Mercator/data/variables"
SSH_DIR="/work/bk1450/b383184/Amazon/Mercator/data/variables_c/tracers"

# Years to process. Override from the command line: sbatch Fix_W_v2.sh 2004 2005
years=("${@:-2004}")

# Force reprocessing of months whose output already exists: FORCE=1 sbatch ...
FORCE="${FORCE:-0}"

# Build the full (year month) job list, skipping months that are already done
# or whose inputs are missing.
jobs=()
for year in "${years[@]}"; do
  for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
    w_out="${OUT_DIR}/W_${year}-${month}fc.nc"
    w_in="${W_IN_DIR}/W_${year}-${month}.nc"
    ssh_in="${SSH_DIR}/SSH_${year}-${month}c.nc"

    if [[ ! -f "$w_in" || ! -f "$ssh_in" ]]; then
      echo "MISSING INPUT ${year}-${month}: need $w_in and $ssh_in -- skipping"
      continue
    fi
    if [[ -f "$w_out" && "$FORCE" != "1" ]]; then
      echo "Output exists for ${year}-${month}, skipping"
      continue
    fi
    jobs+=("${year} ${month}")
  done
done

if [[ ${#jobs[@]} -eq 0 ]]; then
  echo "Nothing to do."
  exit 0
fi

echo "Years requested: ${years[*]}"
echo "Months to process (${#jobs[@]}): ${jobs[*]}"
echo "Distributing across ${SLURM_NTASKS} tasks"

# Round-robin the job list across the SLURM tasks.
for i in $(seq 0 $((SLURM_NTASKS - 1))); do
  my_jobs=()
  for idx in "${!jobs[@]}"; do
    if (( idx % SLURM_NTASKS == i )); then
      my_jobs+=("${jobs[$idx]}")
    fi
  done

  if [[ ${#my_jobs[@]} -eq 0 ]]; then
    echo "Task ${i}: nothing assigned"
    continue
  fi

  echo "Task ${i} handling: ${my_jobs[*]}"

  printf '%s\n' "${my_jobs[@]}" | \
    srun --export=ALL --ntasks=1 --nodes=1 --exclusive -c 16 \
      xargs -n2 -P1 bash -c '
        year=$0
        month=$1
        echo "Processing ${year}-${month}"
        papermill Fix_W.ipynb "executed_W/Fix_W.${year}-${month}.ipynb" \
          -k python \
          -p year "${year}" \
          -p month "${month}" \
          || echo "FAILED ${year}-${month}"
      ' &
done

wait
echo "All tasks completed"
