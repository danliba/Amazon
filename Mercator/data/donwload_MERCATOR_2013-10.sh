#!/bin/bash
#SBATCH --job-name=UVW_2013-10
#SBATCH --nodes=1
#SBATCH --ntasks=1
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

cd /work/bk1450/b383184/Amazon/Mercator/data

export NETRC=/home/b/b383184/.netrc
# tds.mercator-ocean.fr serves an incomplete cert chain (no Sectigo OV R36
# intermediate); this bundle is certifi + that intermediate.
export REQUESTS_CA_BUNDLE=/work/bk1450/b383184/certs/mercator-ca-bundle.pem
export SSL_CERT_FILE=/work/bk1450/b383184/certs/mercator-ca-bundle.pem

mkdir -p logs executed

year=2013
month=10

echo "Downloading ${year}-${month}"

papermill MERCATOR_donwload.ipynb \
  "executed/MERCATOR_donwload.${year}-${month}.ipynb" \
  -k python \
  -p year "${year}" \
  -p month "${month}"

status=$?
if [[ $status -ne 0 ]]; then
  echo "FAILED ${year}-${month} (papermill exit ${status})"
  exit $status
fi

echo "Done ${year}-${month}"
ls -la variables/W_${year}-${month}.nc 2>&1
