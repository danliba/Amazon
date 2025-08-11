#!/bin/bash
#SBATCH --job-name=Atlantic_parcels_2
#SBATCH --ntasks=4  # one per 6 months
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=4
#SBATCH --mem=250G
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
years=({2022..2025})

# Generate dates and filter directly into selected_release_dates
for year in "${years[@]}"; do
  # Set month range: June-Dec for 2022, Jan-June for 2025, Jan-Dec for others
  if [ "$year" -eq 2022 ]; then
    month_range=({6..12})
  elif [ "$year" -eq 2025 ]; then
    month_range=({1..6})
  else
    month_range=({1..12})
  fi
  for month in "${month_range[@]}"; do
    printf -v padded_month "%02d" "$month"
    for day in "${days[@]}"; do
      printf -v padded_day "%02d" "$day"
      date_str="$year-$padded_month-$padded_day"
      # Filter dates between 2022-06-05 and 2025-06-05 (inclusive)
      if [[ "$date_str" > "2022-06-04" && "$date_str" < "2025-06-06" ]]; then
        release_dates+=("$date_str")
      fi
    done
  done
done



# run 185 day batches on each of the four tasks
num_particles=10000
run_time_days=185

# run particles every 5 days from June 06-2022
# Run srun for each date in release_dates, up to 6 tasks in parallel

printf "%s\n" "${release_dates[@]}" | xargs -n1 -P6 -I{} srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "papermill Atlantic_parcels_2.ipynb executed_2/Atlantic_parcels_2.{}.ipynb -k python -p start_time {}T00:00:00 -p num_particles $num_particles -p run_time_days $run_time_days" &

# Wait for all background jobs to complete
wait
