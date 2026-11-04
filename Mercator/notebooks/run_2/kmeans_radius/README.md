# K-means pathways of run_2 particles: radius version

Sibling of `run_2/kmeans` (which clusters the positions at fixed days after
release). Here the clock starts when a particle first crosses **2.5N**, and the
particle is described by **where it first gets farther than 200, 500, 1000, 1500
and 2000 km from its own crossing point** (haversine distance):

```
X_i = [lat_200km, lon_200km, lat_500km, lon_500km, ..., lat_2000km, lon_2000km]
```

The rest is the same method as before: every column standardized to mean 0 /
std 1 (`StandardScaler`), each radius re-weighted by `config.RADIUS_WEIGHTS`
(columns multiplied by `sqrt(w)`), k-means, then clusters merged by hand into
named groups.

**One particle as an example.** It crosses 2.5N at 47W on 2 Apr. Circles of
200 / 500 / 1000 / 1500 / 2000 km are drawn around that point; its features are
the positions where its track first leaves each circle. A fast and a slow
particle on the same route get the same features. The time to reach each
radius is kept (`days_<R>km`) for the diagnostics, but not clustered on.

## Why these radii

Notebook `00_radius_choice` shows it with maps and curves. A 28-store sample
(2026-10-08) gave:

| radius | share of crossing particles that get this far | median days after crossing |
|---|---|---|
| 200 km | 99.6% | 9 |
| 500 km | 99.1% | 15 |
| 1000 km | 97.5% | 32 |
| 1500 km | 89.7% | 51 |
| 2000 km | 73.9% | 73 |
| 2500 km | 48.5% (not used) | 97 |

Every run_2 track ends 185 days after release, so past ~2000 km too many tracks
end first. Not every 100 km: each radius gets equal weight after
standardization, so many small radii would let the near field dominate.

## Particle identity (important for run_2)

run_2 stores had particles deleted, so Parcels IDs have gaps and are **not**
row positions (IDs `4, 5, 8, ...` sit in rows `0, 1, 2`). Every row of the
features / labelled files therefore carries:

| column | example | use |
|---|---|---|
| `store` | `Parcels_run_45678_1999-01-01 00:00:00` | which Zarr store (looked up by name) |
| `row` | `2` | position in that store: `ds.lat.values[row]` |
| `traj` | `8` | Parcels ID, to join with other run_2 outputs |

`pipeline.read_tracks` / `read_paths` read by `row` and check
`ds.trajectory[row] == traj` on every read. `trajectory_id` is only a running
row number over the whole table; nothing is decoded from it. (The day-based
`run_2/kmeans` code still uses `trajectory_id // 10000`, which is wrong for
run_2 stores.)

## Layout

```
kmeans_radius/
├── config.py            paths, LAT_CROSS, RADII_KM, RADIUS_WEIGHTS, GROUP_MAP
├── pipeline.py          crossing, haversine, radius exits, feature extraction, track reader
├── build_notebooks.py   generates the notebooks (OVERWRITES them; `python build_notebooks.py 00` for one)
├── submit_clustering.sh papermill stages on SLURM (STAGES="00 01" / "02" / "03 04")
├── notebooks/
│   ├── 00_radius_choice.ipynb       why these radii (sample of stores, figures)
│   ├── 01_extract_features.ipynb    Stage 1: all stores -> data/features.parquet
│   ├── 02_kmeans_subsample.ipynb    Stage 2 (optional): K sweep, dendrogram
│   ├── 1.5_Manual_clustering.ipynb  by hand: fit, eyeball, assign letters, save model
│   ├── 1.6_Tropical_subclustering.ipynb  by hand: eastward particles only, own K
│   ├── 03_assign_labels.ipynb       Stage 3: label every particle
│   └── 04_diagnostics.ipynb         Stage 4: maps, timing, fractions, representatives
├── data/                features_parts/, features.parquet, kmeans_models/, labeled_trajectories.parquet
└── figures/
```

## Run order

1. `sbatch submit_clustering.sh` runs 00 and 01 (01 reads all 1534 stores).
2. Optional: `sbatch --export=ALL,STAGES="02" submit_clustering.sh` to compare K.
3. Notebook **1.5 by hand**: tune `K` and `RADIUS_WEIGHTS`, fill `ASSIGN`, set
   `SAVE_MODEL = True` and run the save cell, then paste the printed
   `RADIUS_WEIGHTS`, `GROUP_MAP`, `GROUP_NAMES` into `config.py`.
4. Set `BEST_K` in `submit_clustering.sh`, then
   `sbatch --export=ALL,STAGES="03 04" submit_clustering.sh`.
5. Notebook **1.6 by hand** (needs only `features.parquet`): the eastward /
   tropical particles, which the global fit gives only a few clusters, are
   clustered on their own. A particle is kept when the direction from its
   crossing point to its exit at `GATE_R` (default 1000 km) is inside
   `BEARING_RANGE` (default 0-180, i.e. any eastward component; set it from the
   direction histogram in the notebook). `partial` particles are kept: in a
   test almost all eastward particles end their track before 1500-2000 km, so
   those radii are mostly last-position stand-ins and the notebook flags them
   (weight 0 switches a radius off). With `SAVE_MODEL = True` it writes
   `data/kmeans_models/tropical_1.6_k<K>/` and
   `data/tropical_1.6_labels_k<K>.parquet` (store / row / traj per particle).

## Status flags (Stage 1)

| status | meaning | clustering |
|---|---|---|
| `complete` | reached every radius | fit + labels |
| `partial` | reached 200 km, track ended before a larger radius; last position stands in for the missing radii (`days_<R>km` NaN) | labels only |
| `no_gate` | crossed 2.5N but never got 200 km away | not labelled (-1) |
| `no_cross` | never crossed 2.5N | not labelled (-1) |

Crossing rule (same as `analysis/particle_diagnostics/Regroup_particles.ipynb`):
the first output with `lat >= 2.5` whose previous output had `lat < 2.5`. No
run_2 particle starts north of 2.5N.

## Not ported from the day-based project

Notebooks 05-08, 3.6 and the boundary / W / stuck-particle investigations
are tied to the day-based clusters and were left in `run_2/kmeans`.
