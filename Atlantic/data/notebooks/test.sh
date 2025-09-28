#!/bin/bash
#SBATCH --job-name=test_uvw
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=32G
#SBATCH --time=00:10:00
#SBATCH --partition=compute
#SBATCH --account=bk1450

module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

echo "Testing basic setup..."
python -c "import papermill; print('Papermill works')"
ls -la UVW_CMEMS_download.ipynb
mkdir -p executed
echo "Setup complete"