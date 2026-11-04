#!/bin/bash
#SBATCH --job-name=MERCATOR_parcels_1997-1998
#SBATCH --ntasks=8
#SBATCH --ntasks-per-node=1
#SBATCH --nodes=8
#SBATCH --mem=250G
#SBATCH --exclusive
#SBATCH --time=08:00:00
#SBATCH --partition=compute
#SBATCH --account=bk1450

module load python3/2023.01-gcc-11.2.0

source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

num_particles=10000
run_time_days=185
ref_date="1993-01-01"

# Create executed directory
mkdir -p executed

# 8 chunks covering days 1466-2196 (1997-01-05 to 1998-12-31)
# Chunk 1: 1466, 1471, 1476, 1481, 1486, 1491, 1496, 1501, 1506, 1511, 1516, 1521, 1526, 1531, 1536, 1541, 1546, 1551, 1556
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 1466 5 1556 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 2: 1561, 1566, 1571, 1576, 1581, 1586, 1591, 1596, 1601, 1606, 1611, 1616, 1621, 1626, 1631, 1636, 1641, 1646, 1651
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 1561 5 1651 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 3: 1656, 1661, 1666, 1671, 1676, 1681, 1686, 1691, 1696, 1701, 1706, 1711, 1716, 1721, 1726, 1731, 1736, 1741, 1746
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 1656 5 1746 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 4: 1751, 1756, 1761, 1766, 1771, 1776, 1781, 1786, 1791, 1796, 1801, 1806, 1811, 1816, 1821, 1826, 1831 (ends 1997)
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 1751 5 1831 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 5: 1836, 1841, 1846, 1851, 1856, 1861, 1866, 1871, 1876, 1881, 1886, 1891, 1896, 1901, 1906, 1911, 1916, 1921, 1926 (1998)
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 1836 5 1926 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 6: 1931, 1936, 1941, 1946, 1951, 1956, 1961, 1966, 1971, 1976, 1981, 1986, 1991, 1996, 2001, 2006, 2011, 2016, 2021
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 1931 5 2021 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 7: 2026, 2031, 2036, 2041, 2046, 2051, 2056, 2061, 2066, 2071, 2076, 2081, 2086, 2091, 2096, 2101, 2106, 2111, 2116
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 2026 5 2116 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

# Chunk 8: 2121, 2126, 2131, 2136, 2141, 2146, 2151, 2156, 2161, 2166, 2171, 2176, 2181, 2186, 2191, 2196 (ends Dec 31, 1998)
srun --export=ALL --ntasks 1 --nodes 1 --exclusive -c 32 /bin/bash -c -l '
  ref_date="'"$ref_date"'"
  num_particles="'"$num_particles"'"
  run_time_days="'"$run_time_days"'"
  
  seq 2121 5 2196 | xargs -n1 -P5 -I{} \
    papermill MERCATOR_parcels_TS.ipynb \
      executed/MERCATOR_parcels_TS.offset{}.ipynb \
      -k python \
      -p offset {} \
      -p ref_date "$ref_date" \
      -p num_particles "$num_particles" \
      -p run_time_days "$run_time_days"
' &

wait