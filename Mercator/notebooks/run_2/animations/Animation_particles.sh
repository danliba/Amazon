#!/bin/bash
#SBATCH --job-name=particle_videos
#SBATCH --account=bk1450
#SBATCH --partition=compute
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=250G
#SBATCH --time=04:00:00
#SBATCH --output=logs/videos_%j.log
#SBATCH --error=logs/videos_%j.err

# Render particle-trajectory MP4s for the 1993-2013 run_2 production run.
#
#   sbatch Animation_particles.sh                 # all five periods (in parallel, one node)
#   sbatch Animation_particles.sh 1993-1997 2013  # only the named periods
#
# One SLURM job renders every requested period; NEVER submit one job per period
# (the account is limited to a handful of running jobs).

set +u   # conda activate scripts reference unbound vars
module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2

BASE=/work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/animations
cd "$BASE" || exit 1
mkdir -p logs

export MPLBACKEND=Agg
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export MKL_NUM_THREADS=2

# label  start        end
PERIODS=(
  "1993-1997 1993-01-01 1997-12-31"
  "1998-2002 1998-01-01 2002-12-31"
  "2003-2007 2003-01-01 2007-12-31"
  "2008-2012 2008-01-01 2012-12-31"
  "2013      2013-01-01 2013-12-31"
)

# Tunables (see README.md)
N_PARTICLES=${N_PARTICLES:-400}
SPACING=${SPACING:-10}
FRAME_STEP=${FRAME_STEP:-2}
TRAIL_LEN=${TRAIL_LEN:-40}
FPS=${FPS:-6}
DPI=${DPI:-100}
MAX_FRAMES=${MAX_FRAMES:-0}
NPROC=${NPROC:-5}

WANTED=("$@")
want() {
  [ ${#WANTED[@]} -eq 0 ] && return 0
  for w in "${WANTED[@]}"; do [ "$w" = "$1" ] && return 0; done
  return 1
}

render() {   # $1 label  $2 start  $3 end
  local label=$1 start=$2 end=$3
  local out="$BASE/video_particles_${label}"
  mkdir -p "$out"
  echo "[$(date +%T)] START $label ($start .. $end)"
  papermill "$BASE/Animation_particles_period.ipynb" \
            "$out/Animation_particles_${label}_executed.ipynb" \
            -p period_start "$start" \
            -p period_end   "$end" \
            -p n_particles  "$N_PARTICLES" \
            -p release_spacing_days "$SPACING" \
            -p frame_step_days "$FRAME_STEP" \
            -p trail_len    "$TRAIL_LEN" \
            -p fps          "$FPS" \
            -p dpi          "$DPI" \
            -p max_frames   "$MAX_FRAMES" \
            -p out_dir      "$out" \
            -p out_name     "particles_${label}.mp4" \
            > "$BASE/logs/papermill_${label}.log" 2>&1
  local rc=$?
  echo "[$(date +%T)] DONE  $label rc=$rc  -> $out/particles_${label}.mp4"
}
export -f render
export BASE N_PARTICLES SPACING FRAME_STEP TRAIL_LEN FPS DPI MAX_FRAMES

JOBS=()
for spec in "${PERIODS[@]}"; do
  set -- $spec
  want "$1" && JOBS+=("$1 $2 $3")
done
printf '%s\n' "${JOBS[@]}"

printf '%s\n' "${JOBS[@]}" | xargs -P "$NPROC" -I{} bash -c 'render {}'

echo "[$(date +%T)] ALL DONE"
ls -l "$BASE"/video_particles_*/*.mp4
