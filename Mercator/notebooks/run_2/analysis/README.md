# run_2/analysis — spatial-bin analysis of the 1993-2013 Mercator LPT production run

All four release seeds of the new production run are combined here into **one
21-year climatology**:

| seed directory | releases | period |
|---|---|---|
| `../tracks_v3_11098723` | 438 | 1993-1998 |
| `../tracks_v3_45678`    | 439 | 1999-2004 |
| `../tracks_v3_67891`    | 292 | 2005-2008 |
| `../tracks_v3_78876`    | 365 | 2009-2013 |
| **total**               | **1534 zarr stores, 15,485,167 trajectories** | 1993-2013, a release every 5 days |

This redoes the "bin analysis" part of
`../../Analysis/All_tracks_MERCATOR.ipynb` and the seasonality plots of
`../../Analysis/LPT_Seasonality.ipynb`, keeping their method (lon/lat count
histograms of the particle positions, release-month and release-season groups,
obs aggregated into 5-day bins, mean-particle-age map), but computing them by
**streaming the 1534 stores** instead of concatenating them.

## Notebooks

* **`v1.All_tracks_v3.ipynb`** — the computation. First cell is papermill
  `parameters`-tagged (`tracks_dirs`, `out_dir`, `bins_file`,
  obs binning, `n_workers`, `max_stores`, output names). Each store is read once
  in a worker process and binned with **xhistogram** using the template's own
  `calc_hist` / `calc_age` functions
  (`xhist(lon, lat, bins=[lon_bins, lat_bins], dim=["trajectory"])`); the
  resulting `(obs_bin, lon, lat)` counts are accumulated into one master array
  `H[release_year, release_month, obs_bin, lon, lat]`; the monthly and seasonal
  histograms are sums of it. Summing per-store xhist counts is exact - histogram
  counts are additive, so the result is identical to binning the concatenated
  dataset, without ever holding 15.5 M trajectories in memory. Memory stays flat (~1 GB master array + ~1 GB per
  worker). Ends with a verification that the histogram total equals the number
  of particle positions actually read.
  Set `max_stores` to a small number to test on a few stores.
* **`v1.LPT_Seasonality_v3.ipynb`** — the plots, read from the netcdf files
  below; also papermill-parameterised (`analysis_dir`, `fig_dir`, input names,
  `fig_dpi`, map `extent`; `extent=None` = full data extent). Writes PNGs to `figures/`.
* **`v1.All_tracks_v3.sh`** — sbatch wrapper that runs the first notebook on one
  exclusive compute node (account bk1450, partition compute, 250 GB, 04:00:00)
  with papermill, `-p n_workers 48`. Submit from this folder:
  `sbatch v1.All_tracks_v3.sh`. The executed copy lands in
  `executed/v1.All_tracks_v3.out.ipynb`, the SLURM log in `slurm-<jobid>.out`.

## Binning — one shared grid for the whole folder

* **lon/lat bins**: the *template's* scheme
  (`Analysis/All_tracks_MERCATOR.ipynb`), i.e. **bin edges from the data
  extremes**

  ```python
  lat_bins = np.linspace(lat_min, lat_max, 30)
  lon_bins = np.linspace(lon_min, lon_max, 80)
  ```

  which gives **79 x 29 cells of 1.041 deg lon x 1.255 deg lat** over
  96.94W-14.67W, 4.38S-32.02N. Those edges were computed once from the run's
  own extremes by the `v2.*` notebooks and saved to **`v2.bins_v3.npz`**;
  `v1.All_tracks_v3.ipynb` *loads* that file (parameter `bins_file`) instead of
  recomputing, so the histograms, the monthly mean fields
  (`mean_*_month_v3.zarr`) and every figure in this folder sit on exactly the
  same grid. Bin centres are stored as the `lon`/`lat` coordinates, as
  xhistogram does it.
* The earlier 0.5 deg `arange` grid (lon 170 x lat 80 over [-100,-15] x [-8,32])
  is **obsolete**; those `_hist_*_v3.nc` files were deleted and regenerated on
  the grid above, so only one grid exists in this folder.
* obs: the release position (obs 0) is skipped, then obs 1..720 are grouped into
  36 bins of 20 obs = 5 days (6-hourly output); the coordinate
  `days_since_release` gives the centre of each bin in days.
  Stores written with 925 obs are zero/NaT padded beyond obs 739, so nothing is
  lost by using the first 720.
* release year/month/season come from the release time of the store; seasons are
  OND (dry), JFM (transition), AMJ (wet), JAS (transition).

## Output files

| file | contents | dims |
|---|---|---|
| `_hist_year_month_v3.nc` | master histogram, counts by release year and month (int32), variable `histogram_lon_lat` | start_year 21, start_month 12, obs 36, lon 79, lat 29 |
| `_hist_month_v3.nc` | release-month climatology, sum over the 21 years (int64) — equivalent of the old `_hist_month.nc` | start_month 12, obs 36, lon 79, lat 29 |
| `_hist_season_v3.nc` | same, grouped into OND/JFM/AMJ/JAS (int64) | start_season 4, obs 36, lon 79, lat 29 |
| `_hist_age_month_v3.nc` | `mean_age_days` (mean age of the particles in each cell, per release month) and `n_positions` | start_month 12, lon 79, lat 29 |
| `_store_log_v3.csv` | one row per zarr store: path, release date, trajectories, obs on disk, valid/in-range/binned positions |

## Figures (`figures/`)

All maps follow the monthly-map style of `../../Analysis/LPT_Seasonality.ipynb`:
`np.log10(counts).plot.contourf(..., cmap='Spectral_r')` with one shared
horizontal colorbar labelled `log10(counts)`, drawn over the **full data
extent** (96.9W-14.7W, 4.4S-32.0N — out to the African coast), not clipped to
the western tropical Atlantic. The normalised `100*log10(n)/log10(n_max)`
panels of Coles et al. (2013) have been **dropped**.
The `v2.*` PNGs in `figures/` come from the monthly-mean notebooks.

| file | content |
|---|---|
| `monthly_LPT_v3.png` | log10 particle counts, 12 panels by release month (4x3) |
| `season_wet_dry_LPT_v3.png` | log10 counts for OND / JFM / AMJ / JAS |
| `time_residence_LPT_v3.png` | mean particle age per cell, by release month |
| `spreading_time_LPT_v3.png` | log10 counts, AMJ vs OND releases at ~3, 28, 58, 88, 118, 178 days after release |
| `interannual_counts_v3.png` | binned positions per release year/month and the monthly total |
| `occurrence_season_LPT_v3.png` | % of the 5-day windows in which a cell is occupied, per season |
| `pdf_apr_jan_LPT_v3.png` | probability density of the positions, April-to-January releases |
| `pdf_blobs_month_v3.png` | monthly PDFs with the 80th-percentile blob outlined |

## Verification of the run (current, ~1 deg shared grid)

Job **27577688**, 1 exclusive compute node (l40045), 48 worker processes,
elapsed **2 min 43 s** (notebook wall time 1.8 min, streaming pass ~1.9 min),
MaxRSS 66 GB:

* 1534 stores, 15,485,167 trajectories read;
* **11,148,916,804** finite (lon,lat) positions for obs >= 1, of which
  **11,148,916,375** are counted by xhist inside the lon/lat bins — **429
  positions (4e-8 of the total) fall outside the new bin range** and are dropped
  by xhist (the old 0.5 deg range dropped 463);
* the sum of `_hist_month_v3.nc`, of the master year/month array and of the
  age-map counts all equal 11,148,916,375 -> the histograms account for every
  particle position read (`CHECK ... : True` for all three assertions in the
  notebook);
* 72-74 releases in every year from 1993 to 2013;
* cross-check (from the earlier pass, method unchanged): an independent
  `np.bincount` implementation of the same binning gave bit-identical histograms
  and mean-age maps on a 5-store test.

The seasonality notebook was run afterwards on the login node (it only reads the
small netcdf files) and wrote the eight PNGs listed above.

## v3 — Subduction of the particles (`v3.Subduction_v3.ipynb`)

Counterpart of `Analysis/kmeans_analysis/kmean_analysis_30_180_stdZ_w/notebooks/07_retroflection_sinkers.ipynb`
for the v3 production run. That notebook conditioned on a retroflection box and used a
100 m depth cut; this one drops the box (so the *location* of subduction is a result, not
an assumption) and re-tunes the threshold to **50 m**, because in v3 only 0.61 % of
particles ever pass 100 m.

Two independent detectors, because the depth record contains both a slow population-wide
deepening and genuine fast events:

* **threshold crossing** — deepest point of the track exceeds `SUBDUCT_THR` (50 m);
  *sustained* if the particle then stays below it for `PERSIST_DAYS` (5 d);
* **rapid descent** — largest depth gain inside any `RAPID_WIN` (10 d) window exceeds
  `RAPID_DZ` (50 m). Insensitive to the slow drift, so this is the one to quote.

An **age-profile control** (50/90/99th depth percentiles of the whole population against
particle age, split by release month) distinguishes the two.

Papermill-parameterised like the other notebooks; `max_stores > 0` runs a quick test.
All arrays are clamped to the first `max_obs = 740` obs (185 d) because 137 of the 1534
stores are written with 925 obs, NaN-padded past 739.

### Results over the full archive (1534 stores, 15,485,167 trajectories)

| deepest point exceeds | particles | % |
|---|---|---|
| 20 m | 9,568,333 | 61.79 |
| 30 m | 6,440,948 | 41.59 |
| 50 m | 2,372,671 | 15.32 |
| 80 m | 365,543 | 2.36 |
| 100 m | 95,180 | 0.61 |
| 150 m | 2,559 | 0.017 |
| 200 m | 83 | 0.0005 |

* sustained (>5 d below 50 m): 1,824,211 — **11.78 %**, i.e. 76.9 % of the crossings;
* rapid descent (>50 m in 10 d): 421,085 — **2.72 %**;
* deepest particle in the archive: **310.8 m**;
* boundary contact: `ndry > 0` for 1,058 particles (0.007 %) and for **1 crossing** —
  the sub-stepping kernel has closed the grounding pathway, so these depths are physical.
  `nrefine > 0` (8.3 %) only means the kernel refined its step somewhere, and is harmless.

**Where.** Subduction is strongest in the *Caribbean*, but it is **not absent at the
retroflection** — see the two tables below, which answer different questions. The first is
share of all 50 m crossings plus the traffic-normalised rate (crossings in a region divided
by the particles passing through it). It is dominated by traffic, and *understates* regions
few particles visit:

| region | % of crossings | % of rapid events | rate per visitor |
|---|---|---|---|
| plume / Amazon shelf | 0.06 | 0.22 | 0.001 % |
| NBC retroflection (old box, 48-44W / 5-8N) | 0.11 | 0.09 | 0.152 % |
| NBC / Guiana corridor | 2.78 | 2.05 | 0.051 % |
| eastern Caribbean | 27.79 | 16.13 | 0.577 % |
| central / W Caribbean | 39.87 | 59.95 | 1.472 % |
| N of Hispaniola / open Atlantic | 9.11 | 22.55 | 1.232 % |

The conditional map peaks around the Greater Antilles passages (~18-19N, 70-76W) and the
Jamaica / Cayman band (~15-16N, 76-80W), reaching ~20 % in single cells.

The second table conditions on **presence**: of the particles that enter a region, how many
reach a given depth *while they are inside it*. This is the right statistic for "does
subduction happen here", because it removes the traffic effect and does not charge a
particle's first crossing to a single place. 50 m is tuned to the deep Caribbean and is too
blunt for the shallower tropics, so the lower rungs matter.

| region | entering | median age there | >10 m | >20 m | >30 m | >50 m | >80 m |
|---|---|---|---|---|---|---|---|
| plume / Amazon shelf | 2,018,927 | 22 d | 53.52 | 5.74 | 0.63 | 0.02 | 0.01 |
| NBC retroflection (old box) | 50,935 | 119 d | 33.25 | 13.34 | 6.16 | **2.22** | 0.59 |
| NBC / Guiana corridor | 1,955,150 | 67 d | 17.72 | 8.34 | 3.81 | 0.66 | 0.05 |
| eastern Caribbean | 1,585,293 | 119 d | 56.37 | 38.59 | 23.84 | 6.80 | 0.58 |
| central / W Caribbean | 892,604 | 158 d | 64.81 | 51.34 | 38.72 | **18.07** | 3.37 |
| N of Hispaniola / open Atl | 322,910 | 167 d | 62.37 | 45.06 | 30.30 | 12.05 | 1.52 |

So the retroflection box carries a **real** subduction signal — 2.2 % of the particles
entering it pass 50 m while inside, and 13 % pass 20 m, *higher* than the surrounding NBC
corridor (0.66 %) and the plume (0.02 %). It is a local maximum for the tropics, roughly
8x weaker than the central Caribbean. Its tiny share of all crossings (0.11 %) reflects the
fact that only ~0.3 % of particles ever enter that small box, not an absence of subduction.
Note also its median age of 119 d against 67 d for the corridor: the box catches
recirculating, older water rather than fresh through-flow.

**Caveats.** The 185-day run truncates the answer — the crossing-day histogram piles up
near the end of the run and the age profile is still deepening at day 185, so every rate
here is a lower bound. The deepening tracks particle **age**, not calendar season (the
release-month curves largely collapse), so region and age are confounded: particles pass
the retroflection early while still shallow and are in the Caribbean by the time they
subduct. The region comparison should be read with that in mind.

### Outputs

| file | contents |
|---|---|
| `v3.subduction_events_v3.parquet` | one row per particle crossing 50 m (2.37 M): crossing day/position, deepest point, spell length, rapid-descent magnitude/day/position, sigma0 + salinity at release and crossing, `ndry`/`nrefine`, release date/month/year/season |
| `v3.subduction_stores_v3.csv` | per-store totals: trajectories, threshold ladder, crossings, sustained, rapid, boundary contacts, depth percentiles |
| `v3.subduction_ageprofile_v3.npz` | `prof` (1534, 3, 37) depth percentiles vs age, with `ages`, `month`, `year` |
| `v3.subduction_regions_v3.csv` | the traffic-normalised region table |
| `v3.subduction_region_depths_v3.csv` | the conditioned-on-presence region table |
| `figures/v3.subduction_*.png` | histograms, age profile, where (raw + traffic-normalised), regions, seasonality, water mass, examples |

Submit with `sbatch v3.Subduction.sh` (or run locally with papermill; the streaming pass
is ~75 s on 32 workers).
