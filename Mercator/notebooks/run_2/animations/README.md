# Particle-trajectory videos -- run_2 production run (1993-2013)

Two families of MP4s of the Mercator/Parcels `tracks_v3_*` production run:

```
video_particles_1993-2013/particles_1993-2013.mp4   NEW: whole run, cumulative trails, month colours
video_particles_1993-1997/particles_1993-1997.mp4   older: 5-year block, fading trails, day-of-year colours
video_particles_1998-2002/...
video_particles_2003-2007/...
video_particles_2008-2012/...
video_particles_2013/...
```

Each folder also holds the executed papermill notebook that produced its MP4.

--------------------------------------------------------------------------------------------------

## A. The whole-run video (1993-2013, cumulative trails)  -- `Animation_particles_cumulative.ipynb`

`video_particles_1993-2013/particles_1993-2013.mp4`

The run holds **1534 zarr stores** (one release every 5 days, 10061 trajectories x 740 obs each).
This video uses **all** of them:

* **every release** (`release_spacing_days = 5`), 1993-01-06 .. 2013-12-28;
* **1000 trajectories per release**, drawn at random with an RNG seeded from the release date
  (reproducible) -> **1 534 000 trajectories drawn**;
* trajectories are read at `obs_stride = 4`, i.e. one vertex per calendar day (740 obs -> 185 days);
* frames advance in calendar time with `frame_step_days = 2`, at `fps = 6`;
* map extent lon -95..0, lat -10..30 (out to the African coast), figure 1560 x 792 px (dpi 120).

### No fading: cumulative trails

The earlier videos used a `trail_len` window, so particles faded out and disappeared. Here the
trails are **cumulative**: every frame's new track segments are painted onto the canvas and are
**never erased**, so the drawn tracks accumulate over the whole video. Only the bright dots at the
live particle positions and the date label are transient (redrawn each frame).

This is done without redrawing the figure, which is what keeps the cost per frame flat:

1. the map (land, coastlines, gridlines, month legend) is drawn **once**, `fig.canvas.draw()`;
2. `buf = np.asarray(fig.canvas.buffer_rgba())` is a *writable view* of the Agg framebuffer;
3. each frame the new segments go into a throw-away `LineCollection`; `ax.draw_artist(lc)` blits
   them into `buf`, then `lc.remove()` takes the artist off the axes -- the pixels stay, the artist
   is never drawn again;
4. `snap = buf.copy()` records the trails-only state;
5. the live dots and the date text are `draw_artist`-ed on top, `buf` is piped to ffmpeg, and
   `buf[:] = snap` restores the trails-only state (dots and date gone, every trail kept).

`matplotlib.animation.FFMpegWriter` **cannot** be used for this: its `grab_frame()` calls
`savefig`, which redraws the whole figure and would wipe the accumulated canvas. Frames are
therefore written as raw RGBA straight into an ffmpeg pipe (`-f rawvideo -pix_fmt rgba`).

Because the trails accumulate, each single segment must be very faint (`trail_alpha = 0.025`,
`trail_lw = 0.3`) or the core of the plume saturates within the first year. Even so, the busiest
part of the NBC retroflection / Caribbean pathway does saturate towards the end of the 21 years --
that is inherent to "nothing ever disappears" with 1.5M trajectories, and the informative part late
in the video is the frontier and the live dots.

### Colours: release MONTH, qualitative

The older videos coloured releases by day-of-year with the **cyclic** `twilight` colormap, so
December and January looked identical. Here the colour is keyed to the release **month** with 12
deliberately non-cyclic, qualitative colours (tab10 + gold + black), so December (black) and
January (blue) are unmistakably different. A 12-entry legend under the map maps month -> colour.

```
Jan #1f77b4  Feb #ff7f0e  Mar #2ca02c  Apr #d62728  May #9467bd  Jun #8c564b
Jul #e377c2  Aug #7f7f7f  Sep #bcbd22  Oct #17becf  Nov #ffd92f  Dec #000000
```

### Re-rendering

```bash
cd /work/bk1450/b383184/Amazon/Mercator/notebooks/run_2/animations

sbatch Animation_particles_cumulative.sh                                   # the full video
MAX_RELEASES=40 MAX_FRAMES=30 NLOAD=8 sbatch Animation_particles_cumulative.sh   # quick test
TRAIL_ALPHA=0.015 sbatch Animation_particles_cumulative.sh                 # fainter accumulation
```

ONE job (`--account=bk1450 --partition=compute --nodes=1 --exclusive --mem=250G --time=08:00:00`).
Never submit more than one -- the account may only have a few jobs running at a time.

| variable      | notebook parameter      | default | meaning                                       |
|---------------|-------------------------|---------|-----------------------------------------------|
| `LABEL`       | --                      | 1993-2013 | folder/file suffix                          |
| `START`/`END` | `period_start`/`_end`   | 1993-01-06 / 2013-12-28 | release date range             |
| `N_PARTICLES` | `n_particles`           | 1000    | trajectories drawn per release                |
| `SPACING`     | `release_spacing_days`  | 5       | days between drawn releases (5 = every store) |
| `OBS_STRIDE`  | `obs_stride`            | 4       | obs kept at load time (4 = 1 vertex/day)      |
| `FRAME_STEP`  | `frame_step_days`       | 2       | calendar days per frame                       |
| `TRAIL_ALPHA` | `trail_alpha`           | 0.025   | opacity of ONE trail segment (they add up)    |
| `TRAIL_LW`    | `trail_lw`              | 0.3     | trail line width (pt)                         |
| `HEAD_SIZE`   | `head_size`             | 2.5     | size of the live-particle dots                |
| `FPS`         | `fps`                   | 6       | frames per second                             |
| `DPI`         | `dpi`                   | 120     | figure dpi (1560 x 792 px)                    |
| `MAX_FRAMES`  | `max_frames`            | 0       | 0 = full video; N = test render               |
| `MAX_RELEASES`| `max_releases`          | 0       | 0 = all releases; N = test load               |
| `NLOAD`       | `n_load_procs`          | 32      | processes used to read the zarr stores        |

`obs_stride` must stay 4: the render loop assumes one vertex == one calendar day (asserted).

### Loading and cost (measured)

Stores are never concatenated. A `multiprocessing.Pool` of `n_load_procs` workers opens each store,
selects 1000 trajectory indices, reads `lon`/`lat` as float32 at `obs_stride`, and closes it.

* parallel load: **~0.03 s/store effective** with 16-32 workers (serial would be ~0.5 s/store,
  i.e. ~13 min for the whole run);
* in-memory size of the whole run: **~2.3 GB** (1534 x 1000 x 185 x 2 x 4 bytes);
* render, measured with the full steady-state load (37 live releases = ~37 000 live particles,
  ~74 000 new segments per frame): **~1.1 s/frame** at 1560 x 792 -- flat, because only the new
  segments are drawn each frame;
* the full video is ~3950 frames (~11 min at 6 fps) -> **~75 min of rendering**.

Logs: `logs/cumulative_<jobid>.log` / `.err`.

--------------------------------------------------------------------------------------------------

## B. The older five per-period videos -- `Animation_particles_period.ipynb`

`video_particles_1993-1997` ... `video_particles_2013`, in the style of
`/work/bk1450/b383184/Amazon/Atlantic/animations/Animation_science_day.ipynb`
(cartopy map, coloured trails per release date, `trail_len`, `fps`, `dpi`).
**These five MP4s and their notebook are unchanged**; the new video above does not replace them.

* **every 2nd release** (`release_spacing_days = 10`) -> ~183 releases per 5-year block, ~37 for 2013;
* **400 trajectories per release** -> ~73 000 trajectories per 5-year video;
* `frame_step_days = 2` in calendar time; each release lives 185 days, so a steady-state frame holds
  ~19 releases / ~7600 particles;
* colour = cyclic `twilight` on release **day of year** (colorbar on the right) -- note that this
  makes December and January look the same, which is why the new video uses month colours;
* trails are `trail_len = 40` obs (10 days) long, thinned to every 2nd obs, and **fade out**;
* map extent lon -80..-42, lat -2..25, 1200 x 850 px.

```bash
sbatch Animation_particles.sh                 # all five periods, in parallel, inside ONE job
sbatch Animation_particles.sh 2013            # only the 2013 video
sbatch Animation_particles.sh 1993-1997 2013  # a subset
```

| variable      | notebook parameter      | default | meaning                                |
|---------------|-------------------------|---------|----------------------------------------|
| `N_PARTICLES` | `n_particles`           | 400     | trajectories drawn per release         |
| `SPACING`     | `release_spacing_days`  | 10      | days between drawn releases            |
| `FRAME_STEP`  | `frame_step_days`       | 2       | calendar days per frame                |
| `TRAIL_LEN`   | `trail_len`             | 40      | trail length in 6-hourly obs (10 days) |
| `FPS`         | `fps`                   | 6       | frames per second                      |
| `DPI`         | `dpi`                   | 100     | figure dpi (1200x850 px)               |
| `MAX_FRAMES`  | `max_frames`            | 0       | 0 = full video; N = test render        |
| `NPROC`       | --                      | 5       | periods rendered in parallel per job   |

Cost: ~4 s per frame; a 5-year video is ~1000 frames and takes a bit over an hour; the five in
parallel in one job take ~1.5 h wall time.
Logs: `logs/videos_<jobid>.log` (driver) and `logs/papermill_<period>.log` (per period).

--------------------------------------------------------------------------------------------------

## ffmpeg (both families)

The `parcels_3.1.2` conda env has **no** ffmpeg and there is no usable ffmpeg module on Levante.
Both notebooks auto-detect one with libx264 (parameter `ffmpeg_path = ""`):

```
.../site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2    # preferred, static 7.0.2
/sw/spack-levante/mambaforge-23.11.0-0-Linux-x86_64-rb7hor/bin/ffmpeg   # fallback, 6.1.1
```

`/sw/spack-levante/ffmpeg-4.3.2-rmywep/bin/ffmpeg` has **no** libx264 and must not be used.
Output is h264 / yuv420p / crf 23. Frame dimensions must be even for yuv420p (asserted in the
cumulative notebook).

## Environment

```bash
module load python3/2023.01-gcc-11.2.0
source /sw/spack-levante/mambaforge-22.9.0-2-Linux-x86_64-kptncg/etc/profile.d/conda.sh
conda activate /work/bk1450/b383184/conda/envs/parcels_3.1.2
```
