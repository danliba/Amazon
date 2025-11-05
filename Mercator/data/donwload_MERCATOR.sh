#!/bin/bash
#SBATCH --job-name=UVW_CMEMS
#SBATCH --nodes=8
#SBATCH --ntasks=8
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
export NETRC=/home/b/b383184/.netrc

# Create necessary directories
mkdir -p logs executed

# Define the reanalysis folder path
MERCATOR_FOLDER="/work/bk1450/b383184/Amazon/Mercator/data/variables"  # UPDATE THIS PATH

# Define years array
years=(1996 1997 1998 1999 2000 2001 2002 2003)

echo "Starting job with ${SLURM_NTASKS} tasks"
echo "Years to process: ${years[@]}"

for i in $(seq 0 $((SLURM_NTASKS-1))); do
  echo "Starting task $i"
  srun --export=ALL --ntasks=1 --nodes=1 --exclusive -c 16 /bin/bash -lc "
    echo \"Task ${i} starting\"
    
    for idx in {0..7}; do
      if (( idx % ${SLURM_NTASKS} == ${i} )); then
        case \$idx in
          0) year=1996 ;;
          1) year=1997 ;;
          2) year=1998 ;;
          3) year=1999 ;;
          4) year=2000 ;;
          5) year=2001 ;;
          6) year=2002 ;;
          7) year=2003 ;;
        esac
        
        echo \"Processing year: \$year\"

        for month in {01..12}; do
          # Check if U, V, W, T, S files already exist for this year-month
          u_file=\"${MERCATOR_FOLDER}/U_\${year}-\${month}.nc\"
          v_file=\"${MERCATOR_FOLDER}/V_\${year}-\${month}.nc\"
          w_file=\"${MERCATOR_FOLDER}/W_\${year}-\${month}.nc\"
          t_file=\"${MERCATOR_FOLDER}/T_\${year}-\${month}.nc\"
          s_file=\"${MERCATOR_FOLDER}/S_\${year}-\${month}.nc\"
          
          if [[ -f \"\$u_file\" && -f \"\$v_file\" && -f \"\$w_file\" ]]; then
            echo \"Files already exist for \${year}-\${month}, skipping...\"
            continue
          fi

          echo \"Processing \${year}-\${month}\"
          papermill MERCATOR_donwload.ipynb \
            executed/MERCATOR_donwload.\${year}-{}.ipynb \
            -k python \
            -p year \"\$year\" \
            -p month \"{}\"
      fi
    done
    
    echo \"Task ${i} completed\"
  " &
done

wait
echo "All tasks completed"