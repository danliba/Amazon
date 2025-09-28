#!/bin/bash
#SBATCH --job-name=UVW_CMEMS_4
#SBATCH --nodes=4
#SBATCH --ntasks=4
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --exclusive
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450
#SBATCH --output=logs/uvw_%j.out
#SBATCH --error=logs/uvw_%j.err

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

# Create necessary directories
mkdir -p logs executed

# Define the reanalysis folder path
REANALYSIS_FOLDER="/work/bk1450/b383184/Amazon/Atlantic/data/reanalysis"  # UPDATE THIS PATH

# Define years array
years=(2012 2013 2014 2015 2016)

echo "Starting job with ${SLURM_NTASKS} tasks"
echo "Years to process: ${years[@]}"

for i in $(seq 0 $((SLURM_NTASKS-1))); do
  echo "Starting task $i"
  srun --export=ALL --ntasks=1 --nodes=1 --exclusive -c 16 /bin/bash -lc "
    echo \"Task ${i} starting\"
    
    for idx in {0..5}; do
      if (( idx % ${SLURM_NTASKS} == ${i} )); then
        case \$idx in
          0) year=2012 ;;
          1) year=2013 ;;
          2) year=2014 ;;
          3) year=2015 ;;
          4) year=2016 ;;

        esac
        
        echo \"Processing year: \$year\"
        
        for month in {01..12}; do
          # Check if U, V, W files already exist for this year-month
          u_file=\"${REANALYSIS_FOLDER}/U_\${year}-\${month}.nc\"
          v_file=\"${REANALYSIS_FOLDER}/V_\${year}-\${month}.nc\"
          w_file=\"${REANALYSIS_FOLDER}/W_\${year}-\${month}.nc\"
          
          if [[ -f \"\$u_file\" && -f \"\$v_file\" && -f \"\$w_file\" ]]; then
            echo \"Files already exist for \${year}-\${month}, skipping...\"
            continue
          fi
          
          echo \"Processing \${year}-\${month}\"
          papermill UVW_CMEMS_download.ipynb \
            executed/UVW_CMEMS_download.\${year}-\${month}.ipynb \
            -k python \
            -p year \"\$year\" \
            -p month \"\$month\"
        done
      fi
    done
    
    echo \"Task ${i} completed\"
  " &
done

wait
echo "All tasks completed"