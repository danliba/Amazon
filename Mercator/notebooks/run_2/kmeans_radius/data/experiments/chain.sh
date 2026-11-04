#!/bin/bash
# runs inside the interactive allocation: stage 1 -> stage 2 (random weights on best radii set)
set -e
cd /work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/kmeans_radius/data/experiments
PY=/work/bk1450/b383184/conda/envs/parcels_3.1.2/bin/python
export OMP_NUM_THREADS=6
$PY summarize.py stage2 24 > stage1_ranking.txt
$PY eval_configs.py configs_stage2.json 8 > stage2.log 2>&1
$PY summarize.py > final_ranking.txt
echo CHAIN DONE
