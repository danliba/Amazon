# K-Means Trajectory Clustering — Amazon River Plume Pathways (50/100/150-day, z-standardized)

Classify ~16.3 million Lagrangian particle trajectories (OceanParcels / Mercator)
into freshwater pathways by k-means clustering on their positions at the days in
`config.DAYS` (currently **day 30, 50, 100 and 150**), using **per-feature
z-standardization** as the feature scaling (no spherical / haversine embedding),
followed by an optional **per-day weighting** (`config.DAY_WEIGHTS`).

## Why z-standardization (the point of this variant)

k-means minimizes Euclidean distance, and a feature's influence on the result
scales with its **variance across the dataset**. Particles start bunched near the
Amazon mouth and **disperse over time**, so the day-150 positions span a much
larger area than the day-50 positions:

```
Var(day-50) < Var(day-100) < Var(day-150)
```

Left as raw degrees (or embedded on the sphere), the later day therefore
**dominates** the distance — k-means effectively weights the last day the most.
Standardizing each feature `[lat_d, lon_d]` (two columns per day in
`config.DAYS`) to mean 0 / std 1 removes that imbalance and gives **every day
equal weight**. This is exactly:

```
X_std = (x - mean(x)) / std(x)         # per feature, one column at a time
```

A single `sklearn.preprocessing.StandardScaler` is fit on the 200k subsample in
notebook 02, saved to `data/kmeans_models/scaler.pkl`, and reused unchanged in
notebooks 03 (labelling) and 04 (centroids → degrees via `inverse_transform`).

### Per-day weighting (on top of standardization)

Equal weight is the *baseline*. On top of it, `config.DAY_WEIGHTS` deliberately
re-weights each day: after standardizing, each day's two columns are multiplied
by `sqrt(w)` (the per-column vector `W = pipeline.feature_weight_vector()`), which
scales that day's contribution to the k-means squared-distance objective by
exactly `w`. The current weights emphasise the later position:

```
DAY_WEIGHTS = {30: 0.5, 50: 1.0, 100: 1.5, 150: 2.0}   # w per day; W = sqrt(w) per column
```

The *same* `W` is applied at fit time (nb 02), at predict time (nb 03), and is
divided back out before centroids are converted to degrees (nb 02/04). Set every
weight to `1.0` to recover pure equal-weight standardization. **This weighting is
the single source of truth in `config.py`** — do not re-hardcode weights in a
notebook.

This differs from the sibling `kmeans_50_100days` project, which uses two days and
the `xyz`/haversine embedding (`config.FEATURE_SPACE = "xyz"`). Here
`config.FEATURE_SPACE = "zscore"` and `config.DAYS = [30, 50, 100, 150]`.

## Layout

```
kmean_analysis_50_150_stdZ/
├── config.py                 # all paths + parameters (DAYS, FEATURE_SPACE="zscore")
├── pipeline.py               # reusable vectorised functions used by the notebooks
├── build_notebooks.py        # regenerates the notebooks from one source
├── notebooks/
│   ├── 01_extract_features.ipynb   # Stage 1: zarr -> day-30/50/100/150 features
│   ├── 02_kmeans_subsample.ipynb   # Stage 2: subsample, fit StandardScaler + k-means
│   ├── 03_assign_labels.ipynb      # Stage 3: standardize + assign labels to all
│   └── 04_diagnostics.ipynb        # Stage 4: maps, fractions, transit times, table
├── data/
│   ├── features_parts/       # one parquet per store (Stage 1, restartable)
│   ├── features.parquet      # Stage 1 combined output
│   ├── kmeans_models/        # Stage 2 pickles: scaler.pkl + kmeans_k*.pkl
│   └── labeled_trajectories.parquet  # Stage 3 output
└── figures/                  # Stage 2/4 PNGs
```

## Run order

Regenerate the notebooks first (`python build_notebooks.py`), then run `01 → 04`
in order. **Stage 1 must be run in this project** — the four-day feature set
differs from the 50/100-day projects, so `features.parquet` cannot be reused.
After notebook 02, choose your `k` and set `BEST_K` at the top of notebooks 03
and 04.

## Over-resolve, then merge (recommended workflow)

Pick a fairly high k (e.g. 20–25) so the structure is over-resolved into many
fine clusters, then merge the fine clusters that represent the same physical
pathway into a few named groups:

1. In **notebook 02**, section 2.5 draws a Ward dendrogram of the centroids **in
   the standardized space** and prints a suggested `{raw_cluster: group}` map
   (`pipeline.suggest_groups`).
2. Paste/refine that map into `config.GROUP_MAP` (and optionally name groups in
   `GROUP_NAMES`). Any cluster you leave out stays its own singleton group.
3. **Notebook 03** then adds a `cluster_group` column alongside `cluster_label`.
4. In **notebook 04**, set `LABEL_COL = "cluster_group"` to render every figure
   and the summary table at the merged-pathway level (or `"cluster_label"` for
   the raw clusters). Output filenames are suffixed with the chosen level.

`GROUP_MAP` starts empty here (the map is feature-space- and day-count-specific,
so it can't be inherited from the 50/100-day xyz project). Leaving it empty keeps
everything at the raw-cluster level.

## Status flags (Stage 1)

The **gate day** is `DAYS[0]` (currently day 30); a trajectory that never reaches
it is `early_loss`.

| status       | meaning                                              | clustering |
|--------------|------------------------------------------------------|------------|
| `complete`   | valid position at every day in `DAYS` (30, 50, 100 **and** 150) | used for fit + assign |
| `partial`    | reached the gate day (30) but deleted/truncated before one or more later days; last known position used as the proxy for the missing later day(s) | assign only |
| `early_loss` | never reached the gate day (deleted early or store truncated) | excluded (`cluster_label = -1`) |

Note: extending the horizon to day 150 makes the `partial` bucket larger than in
the 50/100-day project (more particles are deleted between day 100 and 150).

## Data facts baked into the code (verified from the zarr metadata)

- Input: `Parcels_run_*.zarr` under `tracks_45678`, `tracks_67891`, `tracks_78876`
  (798 + 510 + 320 = 1,628 stores).
- Output frequency is **6-hourly**; `time` is absolute `datetime64` (NaT after a
  particle is deleted); longitude is already −180..180 (no conversion needed).
- The number of obs **varies per store**; day 50/100/150 are located by **time
  relative to each particle's own release**, not a fixed index.

## Environment

Built and tested against the `parcels_3.1.2` conda env
(`numpy, xarray, zarr, dask, scikit-learn, pandas, pyarrow, cartopy, matplotlib`).
