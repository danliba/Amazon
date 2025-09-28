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

# Create necessary directories
mkdir -p logs executed

# Define years array
years=(1993 1994 1995 1996 1997 1998 1999 2000 2001 2002 2003 2004 2005 2006 2007 2008 2009 2010 2011 2012 2013)

echo "Starting job with ${SLURM_NTASKS} tasks"
echo "Years to process: ${years[@]}"

for i in $(seq 0 $((SLURM_NTASKS-1))); do
  echo "Starting task $i"
  srun --export=ALL --ntasks=1 --nodes=1 --exclusive -c 16 /bin/bash -lc "
    # Re-define years array inside srun context
    years=(1993 1994 1995 1996 1997 1998 1999 2000 2001 2002 2003 2004 2005 2006 2007 2008 2009 2010 2011 2012 2013)
    echo \"Task ${i} starting\"
    
    for idx in \${!years[@]}; do
      if (( idx % ${SLURM_NTASKS} == ${i} )); then
        year=\${years[\$idx]}
        echo \"Processing year: \$year\"
        
        # Process months sequentially to avoid OOM
        seq -w 1 12 | xargs -n1 -P1 -I{} \
          papermill UVW_CMEMS_download.ipynb \
            executed/UVW_CMEMS_download.\${year}-{}.ipynb \
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

# # Define years array - THIS WAS MISSING
# years=(1993 1994 1995 1996 1997 1998 1999 2000 2001 2002 2003 2004 2005 2006 2007 2008 2009 2010 2011 2012 2013)

# echo "Starting job with ${SLURM_NTASKS} tasks"
# echo "Years to process: ${years[@]}"

# for i in $(seq 0 $((SLURM_NTASKS-1))); do
#   echo "Starting task $i"
#   srun --export=ALL --ntasks=1 --nodes=1 --exclusive -c 16 /bin/bash -lc "
#     years=(1993 1994 1995 1996 1997 1998 1999 2000 2001 2002 2003 2004 2005 2006 2007 2008 2009 2010 2011 2012 2013)
#     echo 'Task $i starting'
#     for idx in \${!years[@]}; do
#       if (( idx % ${SLURM_NTASKS} == ${i} )); then
#         year=\${years[\$idx]}
#         echo \"Processing year: \$year\"
#         seq -w 1 12 | xargs -n1 -P2 -I{} \
#           papermill UVW_CMEMS_download.ipynb \
#             executed/UVW_CMEMS_download.\${year}-{}.ipynb \
#             -k python \
#             -p year \"\${year}\" \
#             -p month \"{}\"
#       fi
#     done
#   " &
# done
# wait

# echo "All tasks completed"

# module load python3/2023.01-gcc-11.2.0
# source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
# conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

# years=(1993 1994 1995 1996 1997 1998 1999 2000 2001 2002 2003 2004 2005 2006 2007 2008 2009 2010 2011 2012 2013)

# for i in $(seq 0 $((SLURM_NTASKS-1))); do
#   srun --export=ALL --ntasks=1 --nodes=1 --exclusive -c 16 /bin/bash -lc "
#     for idx in \${!years[@]}; do
#       if (( idx % ${SLURM_NTASKS} == ${i} )); then
#         year=\${years[\$idx]}
#         seq -w 1 12 | xargs -n1 -P2 -I{} \
#           papermill UVW_CMEMS_download.ipynb \
#             executed/UVW_CMEMS_download.\${year}-{}.ipynb \
#             -k python \
#             -p year \"\${year}\" \
#             -p month \"{}\"
#       fi
#     done
#   " &
# done
# wait


# for i in $(seq 0 $((SLURM_NTASKS-1))); do
#   srun --export=ALL --ntasks=1 --nodes=1 --exclusive -c 16 /bin/bash -lc "
#     for idx in \${!years[@]}; do
#       if (( idx % ${SLURM_NTASKS} == ${i} )); then
#         year=\${years[\$idx]}
#         seq -w 1 12 | xargs -n1 -P2 -I{} \
#           papermill UVW_CMEMS_download.ipynb \
#             executed/UVW_CMEMS_download.\${year}-{}-01.ipynb \
#             -k python \
#             -p start_time \"\${year}-{}-01T00:00:00\"
#       fi
#     done
#   " &
# done
# wait

# module load python3/2023.01-gcc-11.2.0

# # Activate your environment if needed
# source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
# conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
# # source /path/to/your/envs/bin/activate


# for year in {1993..2013}; do;
#     for month in {1..12}; do;

#     srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l "seq -w 1 12 | xargs -n1 -P6 -I{} papermill UVW_CMEMS_download.ipynb executed/UVW_CMEMS_download.${year}-{}-01.ipynb -k python -p start_time ${year}-{}-01T00:00:00" & 
# done
# wait 
