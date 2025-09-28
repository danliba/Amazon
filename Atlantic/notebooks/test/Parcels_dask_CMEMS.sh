#!/bin/bash
#SBATCH --job-name=Parcels_dask_CMEMS
#SBATCH --ntasks=6  # 
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=6
#SBATCH --mem=300G
#SBATCH --exclusive
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450

module load python3/2023.01-gcc-11.2.0

# Activate your environment if needed
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
# source /path/to/your/envs/bin/activate

# --- Release dates
# Initialize an empty array for release_dates
declare -a release_dates

# Define arrays for days, months, and years
days=(5 10 15 20 25 30)
months=({1..12})
years=({1993..2020})

# Generate valid dates and store in release_dates
for year in "${years[@]}"; do
  for month in "${months[@]}"; do
    printf -v padded_month "%02d" "$month"
    for day in "${days[@]}"; do
      printf -v padded_day "%02d" "$day"
      date_str="$year-$padded_month-$padded_day"
      # Validate date to exclude invalid ones (e.g., Feb 30)
      if date -d "$date_str" >/dev/null 2>&1; then
        release_dates+=("$date_str")
      fi
    done
  done
done
# ----


# run 185 day batches on each of the four tasks
num_particles=10000
run_time_days=185

# run particles every 5 days from January to 1993-2021
# Run srun for each date in release_dates, up to 6 tasks in parallel

printf "%s\n" "${release_dates[@]}" | xargs -n1 -P6 -I{} srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "papermill Parcels_dask_CMEMS.ipynb executed_2/Parcels_dask_CMEMS.{}.ipynb -k python -p start_time {}T00:00:00 -p num_particles $num_particles -p run_time_days $run_time_days" &

# Wait for all background jobs to complete
wait