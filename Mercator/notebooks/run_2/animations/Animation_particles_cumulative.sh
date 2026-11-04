#!/bin/bash
#SBATCH --job-name=particles_cumulative
#SBATCH --account=bk1450
#SBATCH --partition=compute
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=250G
#SBATCH --time=08:00:00
#SBATCH --output=logs/cumulative_%j.log
#SBATCH --error=logs/cumulative_%j.err

# Render the ONE whole-run (1993-2013) MP4 with cumulative (never-fading) trails and
# qualitative month colours.  See README.md.
#
#   sbatch Animation_particles_cumulative.sh                    # the full 1993-2013 video
#   MAX_FRAMES=40 MAX_RELEASES=60 sbatch Animation_particles_cumulative.sh   # quick test render
#
# This is ONE job.  Never submit several -- the account may only have a few jobs running at a time.

set +u   # conda activate scripts reference unbound vars
module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

BASE=/work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/animations
cd "$BASE" || exit 1
mkdir -p logs

export MPLBACKEND=Agg
# the render loop is single-threaded by construction; keep BLAS from oversubscribing the node
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

LABEL=${LABEL:-1993-2013}
START=${START:-1993-01-06}
END=${END:-2013-12-28}

# Tunables (see README.md)
N_PARTICLES=${N_PARTICLES:-1000}
SPACING=${SPACING:-5}
OBS_STRIDE=${OBS_STRIDE:-4}
FRAME_STEP=${FRAME_STEP:-2}
TRAIL_ALPHA=${TRAIL_ALPHA:-0.025}
TRAIL_LW=${TRAIL_LW:-0.3}
HEAD_SIZE=${HEAD_SIZE:-2.5}
FPS=${FPS:-6}
DPI=${DPI:-120}
MAX_FRAMES=${MAX_FRAMES:-0}
MAX_RELEASES=${MAX_RELEASES:-0}
NLOAD=${NLOAD:-32}

OUT="$BASE/video_particles_${LABEL}"
mkdir -p "$OUT"

echo "[$(date +%T)] START $LABEL ($START .. $END) on $(hostname)"
papermill --log-output "$BASE/Animation_particles_cumulative.ipynb" \
          "$OUT/Animation_particles_${LABEL}_executed.ipynb" \
          -p period_start         "$START" \
          -p period_end           "$END" \
          -p n_particles          "$N_PARTICLES" \
          -p release_spacing_days "$SPACING" \
          -p obs_stride           "$OBS_STRIDE" \
          -p frame_step_days      "$FRAME_STEP" \
          -p trail_alpha          "$TRAIL_ALPHA" \
          -p trail_lw             "$TRAIL_LW" \
          -p head_size            "$HEAD_SIZE" \
          -p fps                  "$FPS" \
          -p dpi                  "$DPI" \
          -p max_frames           "$MAX_FRAMES" \
          -p max_releases         "$MAX_RELEASES" \
          -p n_load_procs         "$NLOAD" \
          -p out_dir              "$OUT" \
          -p out_name             "particles_${LABEL}.mp4"
rc=$?
echo "[$(date +%T)] DONE rc=$rc"
ls -l "$OUT"
