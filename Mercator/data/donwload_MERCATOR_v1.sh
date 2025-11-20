#!/bin/bash
#SBATCH --job-name=UVW_CMEMS
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
export NETRC=/home/b/b383184/.netrc

mkdir -p logs executed

MERCATOR_FOLDER="/work/bk1450/b383184/Amazon/Mercator/data/variables"
years=(2001 2013 2014)

echo "Starting job with ${SLURM_NTASKS} tasks"
echo "Years to process: ${years[@]}"

for i in $(seq 0 $((SLURM_NTASKS-1))); do
  echo "Starting task $i"
  srun --export=ALL --ntasks=1 --nodes=1 --exclusive -c 16 bash -c "
    echo 'Task ${i} starting'
    
    for idx in {0..2}; do
      if (( idx % ${SLURM_NTASKS} == ${i} )); then
        case \$idx in
          0) year=2001 ;;
          1) year=2013 ;;  
          2) year=2014 ;;

        esac
        
        echo 'Processing year:' \$year
        
        # Generate list of months to process (skip existing)
        months_to_process=()
        for month in 01 02 03 04 05 06 07 08 09 10 11 12; do
          u_file='${MERCATOR_FOLDER}/U_'\${year}'-'\${month}'.nc'
          v_file='${MERCATOR_FOLDER}/V_'\${year}'-'\${month}'.nc'
          w_file='${MERCATOR_FOLDER}/W_'\${year}'-'\${month}'.nc'
          t_file='${MERCATOR_FOLDER}/T_'\${year}'-'\${month}'.nc'
          s_file='${MERCATOR_FOLDER}/S_'\${year}'-'\${month}'.nc'
          
          if [[ ! -f \"\$u_file\" || ! -f \"\$v_file\" || ! -f \"\$w_file\" || ! -f \"\$t_file\" || ! -f \"\$s_file\" ]]; then
            months_to_process+=(\${month})
          else
            echo 'Files exist for' \${year}'-'\${month}', skipping'
          fi
        done
        
        # Process months in parallel
        if [ \${#months_to_process[@]} -gt 0 ]; then
          printf '%s\n' \"\${months_to_process[@]}\" | xargs -n1 -P1 -I{} bash -c \"
            echo 'Downloading' \${year}'-{}'
            papermill MERCATOR_donwload.ipynb \
              executed/MERCATOR_donwload.\${year}-{}.ipynb \
              -k python \
              -p year \${year} \
              -p month {}
          \"
        else
          echo 'All files exist for year' \$year', skipping'
        fi
      fi
    done
    
    echo 'Task ${i} completed'
  " &
done

wait
echo "All tasks completed"