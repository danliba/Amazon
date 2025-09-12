#!/bin/bash
#SBATCH --job-name=Atlantic_parcels_100K
#SBATCH --ntasks=46
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=46
#SBATCH --mem=250G
#SBATCH --exclusive
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450

module load python3/2023.01-gcc-11.2.0

# Activate your environment if needed
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

# run 185 day batches on each of the eight tasks
num_particles=100000 #100_000 particles
run_time_days=185
ref_date="2022-01-01"

for offset in $(seq -w 155 50 1255); do
    # Use decimal to avoid octal with leading zeros
    offset_end=$((10#$offset + 45))

    srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
      ref_date="'"$ref_date"'"
      num_particles="'"$num_particles"'"
      run_time_days="'"$run_time_days"'"
      offset_str="'"$offset"'"
      offset_end='"$offset_end"'

      # Generate decimal day numbers (no -w) to avoid octal issues, pass as strings later
      seq '"$((10#$offset))"' 5 "$offset_end" | xargs -n1 -P1 -I{} \
        papermill Atlantic_parcels_4.ipynb \
          executed/Atlantic_parcels_4.y'"${ref_date}"'-offset-days{}.ipynb \
          -k python \
          -p offset {} \
          -p ref_date "$ref_date" \
          -p num_particles "$num_particles" \
          -p run_time_days "$run_time_days"
    ' &
done
wait

# executed/Atlantic_parcels_4.y${ref_date}-offset-days{}.ipynb
# executed/Atlantic_parcels_4.y\${ref_date}.offset-days{}.ipynb \