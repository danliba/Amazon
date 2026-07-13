# K-Means Trajectory Clustering — Amazon River Plume Pathways

Classify ~16.3 million Lagrangian particle trajectories (OceanParcels / Mercator)
into freshwater pathways by k-means clustering on their day-50 and day-100
positions.

## Layout

```
kmeans_analysis/
├── config.py                 # all paths + parameters (edit here)
├── pipeline.py               # reusable vectorised functions used by the notebooks
├── build_notebooks.py        # regenerates the notebooks from one source
├── notebooks/
│   ├── 01_extract_features.ipynb   # Stage 1: zarr -> day-50/day-100 features
│   ├── 02_kmeans_subsample.ipynb   # Stage 2: subsample, fit k-means, evaluate k
│   ├── 03_assign_labels.ipynb      # Stage 3: assign labels to all trajectories
│   └── 04_diagnostics.ipynb        # Stage 4: maps, fractions, transit times, table
├── data/
│   ├── features_parts/       # one parquet per store (Stage 1, restartable)
│   ├── features.parquet      # Stage 1 combined output
│   ├── kmeans_models/        # Stage 2 pickles: kmeans_k10.pkl ... kmeans_k30.pkl
│   └── labeled_trajectories.parquet  # Stage 3 output
└── figures/                  # Stage 2/4 PNGs
```

## Run order

Run the notebooks `01 → 04` in order. Stage 1 is the only heavy step (it streams
all 1,628 zarr stores, 10k trajectories each, one store at a time). After
notebook 02, choose your `k` and set `BEST_K` at the top of notebooks 03 and 04.

## Over-resolve, then merge (recommended workflow)

You don't have to find a single "optimal" k. Pick a fairly high k (e.g. 20–25)
so the structure is over-resolved into many fine clusters, then merge the fine
clusters that represent the same physical pathway into a few named groups:

1. In **notebook 02**, section 2.5 draws a Ward dendrogram of the centroids and
   prints a suggested `{raw_cluster: group}` map (`pipeline.suggest_groups`).
2. Paste/refine that map into `config.GROUP_MAP` (and optionally name groups in
   `GROUP_NAMES`). Any cluster you leave out stays its own singleton group.
3. **Notebook 03** then adds a `cluster_group` column alongside `cluster_label`.
4. In **notebook 04**, set `LABEL_COL = "cluster_group"` to render every figure
   and the summary table at the merged-pathway level (or `"cluster_label"` for
   the raw clusters). Output filenames are suffixed with the chosen level.

Leaving `GROUP_MAP = {}` keeps everything at the raw-cluster level — `cluster_group`
simply mirrors `cluster_label`, so the pipeline works either way.

## Data facts baked into the code (verified from the zarr metadata)

- Input: `Parcels_run_*.zarr` under `tracks_45678`, `tracks_67891`, `tracks_78876`
  (798 + 510 + 320 = 1,628 stores).
- Output frequency is **6-hourly**; `time` is absolute `datetime64` (NaT after a
  particle is deleted); longitude is already −180..180 (no conversion needed).
- The number of obs **varies per store** (925 / 740 / … and some are truncated
  to ~185 obs ≈ 46 days at the end of the forcing). Day-50/day-100 are therefore
  located by **time relative to each particle's own release**, not a fixed index.

## Status flags (Stage 1)

| status       | meaning                                              | clustering |
|--------------|------------------------------------------------------|------------|
| `complete`   | valid position at both day 50 and day 100            | used for fit + assign |
| `partial`    | reached day 50, deleted/truncated before day 100; last known position used as the day-100 proxy | assign only |
| `early_loss` | never reached day 50 (deleted early or store truncated) | excluded (`cluster_label = -1`) |

## Environment

Built and tested against the `parcels_3.1.2` conda env
(`numpy, xarray, zarr, dask, scikit-learn, pandas, pyarrow, cartopy, matplotlib`).
