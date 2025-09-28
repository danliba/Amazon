#!/bin/bash
#SBATCH --job-name=UVW_CMEMS_2
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
years=(2004 2005 2006 2007 2008 2009 2010 2011 2012 2013 2014 2015 2016 2017 2018 2019 2020)

echo "Starting job with ${SLURM_NTASKS} tasks"
echo "Years to process: ${years[@]}"

for i in $(seq 0 $((SLURM_NTASKS-1))); do
  echo "Starting task $i"
  srun --export=ALL --ntasks=1 --nodes=1 --exclusive -c 16 /bin/bash -lc "
    echo \"Task ${i} starting\"
    
    for idx in {0..16}; do
      if (( idx % ${SLURM_NTASKS} == ${i} )); then
        case \$idx in
          0) year=2004 ;;
          1) year=2005 ;;
          2) year=2006 ;;
          3) year=2007 ;;
          4) year=2008 ;;
          5) year=2009 ;;
          6) year=2010 ;;
          7) year=2011 ;;
          8) year=2012 ;;
          9) year=2013 ;;
          10) year=2014 ;;
          11) year=2015 ;;
          12) year=2016 ;;
          13) year=2017 ;;
          14) year=2018 ;;
          15) year=2019 ;;
          16) year=2020 ;;
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

# module load python3/2023.01-gcc-11.2.0
# source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
# conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

# # Create necessary directories
# mkdir -p logs executed

# # Define years array
# years=(2004 2005 2006 2007 2008 2009 2010 2011 2012 2013 2014 2015 2016 2017 2018 2019 2020)

# echo "Starting job with ${SLURM_NTASKS} tasks"
# echo "Years to process: ${years[@]}"

# for i in $(seq 0 $((SLURM_NTASKS-1))); do
#   echo "Starting task $i"
#   srun --export=ALL --ntasks=1 --nodes=1 --exclusive -c 16 /bin/bash -lc "
#     echo \"Task ${i} starting\"
    
#     for idx in {0..17}; do
#       if (( idx % ${SLURM_NTASKS} == ${i} )); then
#         case \$idx in
#           0) year=2004 ;;
#           1) year=2005 ;;
#           2) year=2006 ;;
#           3) year=2007 ;;
#           4) year=2008 ;;
#           5) year=2009 ;;
#           6) year=2010 ;;
#           7) year=2011 ;;
#           8) year=2012 ;;
#           9) year=2013 ;;
#           10) year=2014 ;;
#           11) year=2015 ;;
#           12) year=2016 ;;
#           13) year=2017 ;;
#           14) year=2018 ;;
#           15) year=2019 ;;
#           16) year=2020 ;;
#         esac
        
#         echo \"Processing year: \$year\"
        
#         seq -w 1 12 | xargs -n1 -P1 -I{} \
#           papermill UVW_CMEMS_download.ipynb \
#             executed/UVW_CMEMS_download.\${year}-{}.ipynb \
#             -k python \
#             -p year \"\$year\" \
#             -p month \"{}\"
#       fi
#     done
    
#     echo \"Task ${i} completed\"
#   " &
# done

# wait
# echo "All tasks completed"