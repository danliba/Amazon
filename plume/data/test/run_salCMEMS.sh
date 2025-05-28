#!/bin/bash

#SBATCH --job-name=cmems_download
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=60G
#SBATCH --time=12:00:00
#SBATCH --partition=base
#SBATCH --output=cmems_download_%j.log
#SBATCH --error=cmems_download_error_%j.log

# Load necessary modules
module load gcc12-env/12.3.0 
module load singularity/3.11.5

# Define paths
container_path="/gxfs_work/geomar/smomw662/FESOMparcels_first/parcels-container_2024.10.03-921b2b0.sif"
python_script="sak_CMEMS.py"

# Run the Python script inside the container with package installation
srun --ntasks=1 --exclusive singularity exec -B /gxfs_work:/gxfs_work -B $PWD:/work --pwd /work "${container_path}" bash -c \
    ". /opt/conda/etc/profile.d/conda.sh && conda activate base \
    && pip install copernicusmarine \
    && python ${python_script}"