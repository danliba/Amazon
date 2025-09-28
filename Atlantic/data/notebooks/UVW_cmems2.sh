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
    echo \"Task ${i} starting\"
    
    for idx in {0..20}; do
      if (( idx % ${SLURM_NTASKS} == ${i} )); then
        case \$idx in
          0) year=1993 ;;
          1) year=1994 ;;
          2) year=1995 ;;
          3) year=1996 ;;
          4) year=1997 ;;
          5) year=1998 ;;
          6) year=1999 ;;
          7) year=2000 ;;
          8) year=2001 ;;
          9) year=2002 ;;
          10) year=2003 ;;
          11) year=2004 ;;
          12) year=2005 ;;
          13) year=2006 ;;
          14) year=2007 ;;
          15) year=2008 ;;
          16) year=2009 ;;
          17) year=2010 ;;
          18) year=2011 ;;
          19) year=2012 ;;
          20) year=2013 ;;
        esac
        
        echo \"Processing year: \$year\"
        
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