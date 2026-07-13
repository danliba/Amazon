"""Generate the four pipeline notebooks with nbformat.

Run once:  python build_notebooks.py
Re-run any time to regenerate the notebooks from this single source.

This is the z-standardized, N-day variant: positions are sampled at the days in
`config.DAYS`, the raw [lat, lon] features are standardized to mean 0 / std 1 by a
StandardScaler (saved in `data/kmeans_models/scaler.pkl`), then optionally
re-weighted per day by `config.DAY_WEIGHTS` (the per-column vector
`W = pipeline.feature_weight_vector()`), and k-means is fit in that weighted
standardized space.  The SAME `W` is reapplied at predict time (nb 03) and
divided back out before centroids are converted to degrees (nb 02/04) -- so the
weighting must never live only inside one notebook.
"""
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell
from pathlib import Path

NB_DIR = Path(__file__).resolve().parent / "notebooks"
NB_DIR.mkdir(exist_ok=True)


def md(s):
    return new_markdown_cell(s.strip("\n"))


def code(s):
    return new_code_cell(s.strip("\n"))


def params_code(s):
    """A code cell tagged `parameters` so papermill can override these values
    with `-p name value` at execution time (batch / SLURM runs)."""
    c = new_code_cell(s.strip("\n"))
    c.metadata["tags"] = ["parameters"]
    return c


def save(name, cells):
    nb = new_notebook(cells=cells)
    nb.metadata.kernelspec = {
        "display_name": "Python 3", "language": "python", "name": "python3"
    }
    nb.metadata.language_info = {"name": "python"}
    path = NB_DIR / name
    nbf.write(nb, path)
    print("wrote", path)


# Common header injected at the top of every notebook so that `config` and
# `pipeline` (which live one directory up) are importable.
BOOT = """
import sys, os
sys.path.insert(0, os.path.abspath(".."))   # project root: config.py, pipeline.py
import numpy as np
import pandas as pd
import config as C
import pipeline as P
print("project root:", C.PROJECT_ROOT)
print("sampling days:", C.DAYS, "| feature space:", C.FEATURE_SPACE)
"""

# ===========================================================================
# Notebook 01 -- Stage 1: extract features
# ===========================================================================
save("01_extract_features.ipynb", [
    md("""
# 01 - Extract Feature Vectors  (Stage 1)

**Purpose.** Read every Parcels Zarr store and, for each trajectory, record the
particle position at each day in `config.DAYS` (**30, 50, 100, 150 days** after
*its own* release):

`X_i = [lat_30, lon_30, lat_50, lon_50, lat_100, lon_100, lat_150, lon_150]`

plus the release date / month / year and a survival `status`.

**Inputs.**  ~1,628 `Parcels_run_*.zarr` stores (10,000 trajectories each)
listed by `config.list_stores()`.

**Output.**  `data/features.parquet` (one row per trajectory).

**Notes about this dataset (verified from the Zarr metadata):**
- Output frequency is **6-hourly**, time is absolute `datetime64` (NaT after a
  particle is deleted), longitude is already in -180..180, so no conversion.
- The number of obs **varies per store** (925 / 740 / ... and some are
  truncated to ~185 obs ≈ 46 days at the end of the forcing data). Each day in
  `DAYS` is therefore found by *time*, not a fixed index; truncated stores fall
  out as `early_loss` / `partial` automatically. Adding day 150 means noticeably
  more particles are `partial` (deleted between day 100 and 150) than in the
  50/100-day project.
"""),
    code(BOOT),
    md("## 1.1  Configuration"),
    code("""
stores = C.list_stores()
print(f"{len(stores)} stores  ->  ~{len(stores)*C.TRAJ_PER_STORE:,} trajectories")
print("sampling days:", C.DAYS, "| tolerance(d):", C.TIME_TOL_DAYS)
print("writing per-store parts to:", C.FEATURE_PARTS_DIR)
stores[:3]
"""),
    md("""
## 1.2  Sanity check on a single store

`pipeline.extract_store_features` does the vectorised work: it converts each
obs time to *days since that particle's release*, finds the nearest valid obs to
each day in `DAYS`, and assigns the status. Inspect one store first.
"""),
    code("""
df0 = P.extract_store_features(stores[0], 0)
print(df0.status.value_counts())
df0.head()
"""),
    code("""
# Quick scatter of the first 1000 positions at each day as a sanity check.
import matplotlib.pyplot as plt
sub = df0[df0.status == "complete"].head(1000)
fig, ax = plt.subplots(figsize=(6, 5))
for d in C.DAYS:
    ax.scatter(sub[f"lon_{d}"], sub[f"lat_{d}"], s=4, label=f"day {d}")
ax.set_xlabel("lon"); ax.set_ylabel("lat"); ax.legend(); ax.set_title("store 0 sample")
plt.show()
"""),
    md("""
## 1.3  Process all stores (parallel across stores)

Each store is independent, so we process them **in parallel with joblib** (one
process per store, `loky` backend, so the NumPy work sidesteps the GIL). We write
one small parquet per store into `data/features_parts/`. This keeps memory flat
(one store = 10k rows per worker) and makes the loop restartable: already-written
parts are skipped, so re-running only fills the gaps.

Set `N_JOBS` to the cores you actually have. In a SLURM job it defaults to
`$SLURM_CPUS_PER_TASK`. Do **not** also start a dask `Client` here — pick one
parallelism scheme, not both.
"""),
    code("""
from joblib import Parallel, delayed

N_JOBS = int(os.environ.get("SLURM_CPUS_PER_TASK", 8))   # cores to use

def _extract_one(i, s):
    part = C.FEATURE_PARTS_DIR / f"part_{i:05d}.parquet"
    if part.exists():
        return None                      # restartable: skip finished stores
    P.extract_store_features(s, i).to_parquet(part, index=False)
    return i

print(f"extracting {len(stores)} stores with n_jobs={N_JOBS} ...")
Parallel(n_jobs=N_JOBS, backend="loky", verbose=10)(
    delayed(_extract_one)(i, s) for i, s in enumerate(stores)
)
print("done -> wrote", len(list(C.FEATURE_PARTS_DIR.glob('part_*.parquet'))), "parts")
"""),
    md("## 1.4  Combine parts into a single `features.parquet`"),
    code("""
parts = sorted(C.FEATURE_PARTS_DIR.glob("part_*.parquet"))
features = pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True)
features.to_parquet(C.FEATURES_FILE, index=False)
print("combined shape:", features.shape, "->", C.FEATURES_FILE)
"""),
    md("## 1.5  Summary"),
    code("""
vc = features.status.value_counts()
print(f"Extracted features for {len(features):,} trajectories.")
for k in ["complete", "partial", "early_loss"]:
    print(f"  {k:10s}: {vc.get(k,0):,}")
print(f"release years: {features.release_year.min()}-{features.release_year.max()}")
print(f"Saved to {C.FEATURES_FILE}")
"""),
])

# ===========================================================================
# Notebook 02 -- Stage 2: k-means on subsample
# ===========================================================================
save("02_kmeans_subsample.ipynb", [
    md("""
# 02 - K-Means on a Subsample  (Stage 2)

**Purpose.** Fit `MiniBatchKMeans` on a 200k subsample of `complete`
trajectories for several `k`, evaluate each `k` (inertia, silhouette, cluster
sizes, maps), and pickle every model so the best `k` can be chosen later.

**Input.** `data/features.parquet`  (Stage 1).
**Output.** `data/kmeans_models/scaler.pkl` (the shared StandardScaler),
`data/kmeans_models/kmeans_k*.pkl`, evaluation plots in `figures/`.

**Feature handling — z-standardization (this project's whole point).** The raw
features are the `2 × len(C.DAYS)` numbers `[lat_d, lon_d]` for every day in
`config.DAYS` (currently `[30, 50, 100, 150]` → `[lat_30, lon_30, …, lat_150,
lon_150]`) in degrees (`pipeline.build_feature_matrix`). We then **standardize
every column to mean 0 / std 1** with a single `StandardScaler` fit on the
subsample. This is what gives each day **equal weight**: particles disperse over
time, so the later day has the largest spatial variance and would otherwise
dominate the Euclidean distance k-means minimizes (k-means would effectively
weight the last day the most). Standardizing removes that bias. There is **no
spherical / haversine embedding** here — that would re-introduce a variance
imbalance. The scaler is saved and reused unchanged in notebooks 03 and 04.

**Per-day weighting (on top of standardization).** After standardizing, we
optionally re-weight each day on purpose via `config.DAY_WEIGHTS` (built into the
per-column multiplier `W = pipeline.feature_weight_vector()`, `W = sqrt(w)` per
column). Multiplying a standardized column by `sqrt(w)` scales its variance — and
hence that day's contribution to the k-means squared-distance objective — by
exactly `w`, letting the later position get more say. The *same* `W` is reapplied
in notebooks 03 (predict) and 04 (centroids → degrees, dividing by `W`); set every
weight to 1.0 for pure equal-weight standardization.
"""),
    code(BOOT),
    md("## 2.1  Load features, take a 200k subsample, fit & save the StandardScaler"),
    code("""
import pickle
from sklearn.preprocessing import StandardScaler

features = pd.read_parquet(C.FEATURES_FILE)
complete = features[features.status == "complete"]
n_sub = min(C.N_SUB, len(complete))
sub = complete.sample(n=n_sub, random_state=C.RANDOM_STATE)

X_raw = P.build_feature_matrix(sub)          # raw degrees: [lat50,lon50,...,lon150]
scaler = StandardScaler().fit(X_raw)         # mean 0 / std 1 per column
X_sub = scaler.transform(X_raw)              # standardized space k-means sees
with open(C.MODELS_DIR / "scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)

print(f"complete: {len(complete):,}  ->  subsample: {X_sub.shape}")
print("feature columns:", P.feature_columns())
print("feature order          :", P.feature_columns())
print("per-column mean (deg)  :", np.round(scaler.mean_, 2))
print("per-column std  (deg)  :", np.round(scaler.scale_, 2),
      "  <- note how the later day has the larger spread that standardization equalizes")
print("after scaling -> mean  :", np.round(X_sub.mean(axis=0), 2), " (expect ~0)")
print("after scaling -> std   :", np.round(X_sub.std(axis=0), 2), " (expect ~1 -> equal weight per day)")
"""),
    md("## 2.1b  Per-day weighting (applied AFTER z-standardization)"),
    code("""
# Columns are [lat_d, lon_d] per day in C.DAYS, e.g.
#   [lat_30, lon_30, lat_50, lon_50, lat_100, lon_100, lat_150, lon_150]
# In z-scored space every day already has equal variance (std=1). Multiplying a
# column by sqrt(w) scales its variance by w, so w is the effective weight of
# that day's squared distance in the k-means objective. Later days get more say
# (where did the particle end up?).
#
# The weights live in config.DAY_WEIGHTS (single source of truth) and the
# per-column multiplier W is built by pipeline.feature_weight_vector(), so
# notebooks 03 (predict) and 04 (centroid degrees) apply the SAME weighting
# instead of silently dropping it.
W = P.feature_weight_vector()   # sqrt(w) per column, aligned to P.feature_columns()
assert W.shape[0] == X_sub.shape[1], "W must have one entry per feature column"

# Reassign X_sub IN PLACE of the plain standardized matrix so EVERYTHING
# downstream (k-means fit, predict, centroid plots) sees the weighting.
# Rebuilt from X_raw each run, so re-executing this cell is idempotent.
X_sub = scaler.transform(X_raw) * W

print("per-day weights   :", C.DAY_WEIGHTS)
print("per-column sqrt(w):", dict(zip(P.feature_columns(), W.round(3))))
print("weighted std      :", np.round(X_sub.std(axis=0), 3),
      " (each pair now ~sqrt(w); was ~1)")
"""),
    md("## 2.2  Fit MiniBatchKMeans for each k and evaluate (in standardized space)"),
    code("""
import time
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import silhouette_score

results = []
for k in C.K_LIST:
    t0 = time.time()
    km = MiniBatchKMeans(n_clusters=k, random_state=C.RANDOM_STATE,
                         batch_size=10000, n_init=10, max_iter=300)
    labels = km.fit_predict(X_sub)
    sil = silhouette_score(X_sub, labels, sample_size=C.SILHOUETTE_SAMPLE,
                           random_state=C.RANDOM_STATE)
    sizes = np.bincount(labels, minlength=k)
    with open(C.MODELS_DIR / f"kmeans_k{k}.pkl", "wb") as f:
        pickle.dump(km, f)
    results.append(dict(k=k, inertia=km.inertia_, silhouette=sil,
                        min_size=sizes.min(), max_size=sizes.max()))
    print(f"k={k:2d}  inertia={km.inertia_:.1f}  silhouette={sil:.3f}  "
          f"sizes[{sizes.min()}..{sizes.max()}]  ({time.time()-t0:.1f}s)")

res = pd.DataFrame(results)
res
"""),
    md("## 2.3  Elbow and silhouette plots"),
    code("""
import matplotlib.pyplot as plt
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
a1.plot(res.k, res.inertia, "o-"); a1.set_xlabel("k"); a1.set_ylabel("inertia")
a1.set_title("Elbow plot")
a2.plot(res.k, res.silhouette, "o-"); a2.set_xlabel("k")
a2.set_ylabel("silhouette"); a2.set_title("Silhouette vs k")
fig.tight_layout()
fig.savefig(C.FIG_DIR / "elbow_plot.png", dpi=130)
fig.savefig(C.FIG_DIR / "silhouette_plot.png", dpi=130)
plt.show()
"""),
    md("""
## 2.4  Cluster maps for each k

For every `k`, colour the subsample's positions by cluster label so the spatial
structure can be judged by eye: day 50 = dots, day 100 = x, day 150 = +.
"""),
    code("""
markers = {C.DAYS[0]: ".", }
fig, axes = plt.subplots(1, len(C.K_LIST), figsize=(4*len(C.K_LIST), 4), squeeze=False)
mk = ["o", "x", "+", "s", "d"]
for ax, k in zip(axes[0], C.K_LIST):
    with open(C.MODELS_DIR / f"kmeans_k{k}.pkl", "rb") as f:
        km = pickle.load(f)
    lab = km.predict(X_sub)
    for j, d in enumerate(C.DAYS):
        ax.scatter(sub[f"lon_{d}"], sub[f"lat_{d}"], c=lab, s=2, cmap="tab20",
                   marker=mk[j % len(mk)], alpha=.4)
    ax.set_title(f"k={k}"); ax.set_xlabel("lon"); ax.set_ylabel("lat")
fig.tight_layout()
fig.savefig(C.FIG_DIR / "cluster_maps_by_k.png", dpi=120)
plt.show()
"""),
    md("""
## 2.5  Suggested cluster groupings (over-resolve, then merge)

We are **not** looking for a single "optimal" k. Instead pick a fairly high k
(e.g. 20-25) so the structure is over-resolved into many fine clusters, then
merge the fine clusters that represent the *same* physical pathway into a few
named groups.

The dendrogram below performs a Ward hierarchical clustering on the chosen
model's centroids **in the standardized space k-means was fit in** (so the merge
distances are consistent with the clustering). `pipeline.suggest_groups` cuts
that tree into `n_groups` and returns a `{raw_cluster: group}` map you can paste
into `config.GROUP_MAP` (and then refine by eye).
"""),
    code("""
from scipy.cluster.hierarchy import dendrogram

INSPECT_K = 20     # the k you want to take forward and group
N_GROUPS  = 6      # how many merged pathway groups you want to end up with

with open(C.MODELS_DIR / f"kmeans_k{INSPECT_K}.pkl", "rb") as f:
    km_i = pickle.load(f)
# Centroids live in WEIGHTED standardized space -> divide by W to undo the
# per-day weighting before inverse_transform gives back real degrees.
cent_deg = P.centroids_to_degrees(km_i.cluster_centers_ / W, scaler)   # readable labels
# Grouping is done in the weighted space k-means was fit in (keep the weights).
group_map, Z = P.suggest_groups(km_i.cluster_centers_, N_GROUPS)

fig, ax = plt.subplots(figsize=(11, 4))
dendrogram(Z, labels=[f"{c}" for c in range(INSPECT_K)], ax=ax,
           color_threshold=Z[-(N_GROUPS-1), 2])
ax.set_title(f"Centroid dendrogram (k={INSPECT_K}); cut -> {N_GROUPS} groups")
ax.set_xlabel("raw cluster id"); ax.set_ylabel("Ward distance (weighted std space)")
fig.savefig(C.FIG_DIR / f"centroid_dendrogram_k{INSPECT_K}.png", dpi=130, bbox_inches="tight")
plt.show()

print("Suggested GROUP_MAP (paste into config.py, then refine):")
print("GROUP_MAP =", group_map)
for g in sorted(set(group_map.values())):
    members = [c for c, gg in group_map.items() if gg == g]
    print(f"  group {g}: clusters {members}")
"""),
    md("""
### Numbered centroid map (eyeball the grouping alongside the dendrogram)

One big, readable map of the `k={INSPECT_K}` centroids in real degrees. Each
cluster's mean pathway is drawn day 50 -> 100 -> 150 (small -> large marker,
black edge on the final day); the cluster **number** sits at the day-150 end,
haloed in its **suggested group** colour. Read it together with the dendrogram:
numbers sharing a halo colour are the clusters `suggest_groups` wants to merge.
The map auto-fits to the centroids so nothing is cropped.
"""),
    code("""
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
import cartopy.crs as ccrs, cartopy.feature as cfeature

cl_cmap   = plt.get_cmap("tab20", INSPECT_K)
grp_ids   = sorted(set(group_map.values()))
grp_cmap  = plt.get_cmap("Set1", max(len(grp_ids), 3))
grp_color = {g: grp_cmap(i) for i, g in enumerate(grp_ids)}

pc = ccrs.PlateCarree()
fig = plt.figure(figsize=(11, 8))
ax = plt.axes(projection=pc)
# auto-fit to the centroids (day150 disperses far) so nothing is cropped
lat_all = cent_deg[:, 0::2]; lon_all = cent_deg[:, 1::2]
ax.set_extent([lon_all.min()-3, lon_all.max()+3,
               lat_all.min()-3, lat_all.max()+3], crs=pc)
ax.add_feature(cfeature.LAND, facecolor="0.85"); ax.coastlines(lw=.5)
gl = ax.gridlines(draw_labels=True, lw=.3, color="0.7", alpha=.5)
gl.top_labels = gl.right_labels = False

day_sizes = [16, 45, 95, 95, 95, 95]   # grow with day so start/end are obvious
for c in range(INSPECT_K):
    lats = cent_deg[c, 0::2]; lons = cent_deg[c, 1::2]   # one entry per day in C.DAYS
    ax.plot(lons, lats, "-", color=cl_cmap(c), lw=1.5, alpha=.7, transform=pc)
    for j in range(len(C.DAYS)):
        ax.scatter(lons[j], lats[j], s=day_sizes[j % len(day_sizes)], color=cl_cmap(c),
                   edgecolor="k" if j == len(C.DAYS) - 1 else "none", lw=.5,
                   zorder=3, transform=pc)
    # cluster number at the LAST day, haloed in its suggested group colour
    ax.text(lons[-1], lats[-1], str(c), fontsize=11, fontweight="bold",
            ha="center", va="center", color="white", zorder=4, transform=pc,
            path_effects=[pe.withStroke(linewidth=3, foreground=grp_color[group_map[c]])])

ax.set_title(f"Centroids day {' -> '.join(map(str, C.DAYS))} (k={INSPECT_K}); "
             f"halo = suggested group ({N_GROUPS}). Compare with the dendrogram.")
ax.legend(handles=[Line2D([0], [0], marker="o", ls="", mfc=grp_color[g], mec="k",
                          label=f"group {g}") for g in grp_ids], fontsize=8, loc="best")
fig.savefig(C.FIG_DIR / f"centroid_map_k{INSPECT_K}.png", dpi=130, bbox_inches="tight")
plt.show()
"""),
    md("""
## 2.6  Summary

Models for every k are pickled in `data/kmeans_models/` alongside the shared
`scaler.pkl`. Decide:
1. which **k** to carry forward (set `BEST_K` in notebooks 03 & 04), and
2. (optionally) the **GROUP_MAP** that merges fine clusters into pathway groups
   (paste into `config.py`).

If you set `GROUP_MAP`, notebooks 03 and 04 will additionally produce a
`cluster_group` column and group-level figures; if you leave it empty they fall
back to the raw clusters.
"""),
    code("""
print("scaler saved:", (C.MODELS_DIR / "scaler.pkl").exists())
print("models saved:", sorted(p.name for p in C.MODELS_DIR.glob('kmeans_k*.pkl')))
print(res.to_string(index=False))
"""),
])

# ===========================================================================
# Notebook 03 -- Stage 3: assign labels to all
# ===========================================================================
save("03_assign_labels.ipynb", [
    md("""
# 03 - Assign Cluster Labels to ALL Trajectories  (Stage 3)

**Purpose.** Load the chosen k-means model **and the saved StandardScaler**, and
assign a `cluster_label` to every trajectory by nearest-centroid lookup
(`predict`, no iteration). The scaler from notebook 02 must be applied to the raw
features before `predict`, so every trajectory is standardized with the *same*
means/stds the model was trained on.

- `complete` and `partial` trajectories are labelled (for `partial`, the last
  known position was already used as the proxy for the missing later day(s) in
  Stage 1).
- `early_loss` trajectories have no usable features -> `cluster_label = -1`.

If `config.GROUP_MAP` is set, a merged `cluster_group` column is also added;
otherwise `cluster_group` mirrors `cluster_label`.

**Input.** `data/features.parquet`, `data/kmeans_models/kmeans_k{BEST_K}.pkl`,
`data/kmeans_models/scaler.pkl`.
**Output.** `data/labeled_trajectories.parquet`.
"""),
    code(BOOT),
    md("## 3.1  Choose k and load the model + scaler"),
    params_code("""
BEST_K = 20          # <-- set after inspecting notebook 02 (papermill: -p BEST_K <k>)
"""),
    code("""
import pickle
with open(C.MODELS_DIR / f"kmeans_k{BEST_K}.pkl", "rb") as f:
    km = pickle.load(f)
with open(C.MODELS_DIR / "scaler.pkl", "rb") as f:
    scaler = pickle.load(f)
print("loaded model with", km.n_clusters, "clusters and the shared StandardScaler")
"""),
    md("## 3.2  Predict labels for every labellable trajectory"),
    code("""
features = pd.read_parquet(C.FEATURES_FILE)
labelable = features.status != "early_loss"
# Standardize with the SAME scaler, then apply the SAME per-day weighting the
# model was fit with (config.DAY_WEIGHTS via pipeline.feature_weight_vector()).
# The k-means centroids live in this weighted space, so predict MUST see it too;
# omitting * W would assign labels in a different space than the model was fit in.
W = P.feature_weight_vector()
X_all = scaler.transform(P.build_feature_matrix(features[labelable])) * W
labels = np.full(len(features), -1, dtype=np.int32)
labels[labelable.to_numpy()] = km.predict(X_all).astype(np.int32)
features["cluster_label"] = labels
print(features.cluster_label.value_counts().sort_index().to_string())
"""),
    md("""
## 3.2b  Merge into pathway groups (optional)

If `config.GROUP_MAP` is non-empty, merge the raw clusters into groups; the
result is stored in `cluster_group`. With an empty map, `cluster_group` simply
equals `cluster_label`.
"""),
    code("""
if C.GROUP_MAP:
    groups, raw2grp = P.apply_group_map(features.cluster_label.to_numpy(), C.GROUP_MAP, BEST_K)
    features["cluster_group"] = groups.astype(np.int32)
    print("raw cluster -> group:", raw2grp)
    print(features.loc[features.cluster_group >= 0, "cluster_group"]
          .value_counts().sort_index().to_string())
else:
    features["cluster_group"] = features["cluster_label"]
    print("GROUP_MAP empty -> cluster_group mirrors cluster_label")
"""),
    md("## 3.3  Save labelled trajectories"),
    code("""
features.to_parquet(C.LABELED_FILE, index=False)
print("saved", features.shape, "->", C.LABELED_FILE)
"""),
    md("## 3.4  Summary"),
    code("""
lbl = features[features.cluster_label >= 0]
print(f"Labelled {len(lbl):,} trajectories into {BEST_K} clusters "
      f"({(features.cluster_label==-1).sum():,} early_loss left unlabelled).")
print(f"Saved to {C.LABELED_FILE}")
"""),
])

# ===========================================================================
# Notebook 04 -- Stage 4: diagnostics & figures
# ===========================================================================
save("04_diagnostics.ipynb", [
    md("""
# 04 - Diagnostics and Figures  (Stage 4)

**Purpose.** Produce the pathway map, seasonal & interannual fractions, transit
time distributions, centroid map (day 50 / 100 / 150), and the pathway summary
table for the chosen `k`.

**Input.** `data/labeled_trajectories.parquet` (Stage 3), the chosen k-means
model, the saved `scaler.pkl`, and the original Zarr stores (for full trajectory
paths / transit times).
**Output.** PNGs in `figures/` and a printed summary table.
"""),
    code(BOOT),
    md("""
**Raw clusters vs. merged groups.** Set `LABEL_COL = "cluster_group"` to make
every figure at the merged-pathway level (requires a `GROUP_MAP` in `config`),
or `"cluster_label"` for the raw k-means clusters. Everything below keys off
`LABEL_COL`, so the figures, fractions and table all follow your choice.
"""),
    params_code("""
BEST_K = 20                    # <-- must match notebook 03 (papermill: -p BEST_K <k>)
LABEL_COL = "cluster_group"    # "cluster_group" (merged) or "cluster_label" (raw)
"""),
    code("""
import pickle, matplotlib.pyplot as plt
lab = pd.read_parquet(C.LABELED_FILE)
with open(C.MODELS_DIR / f"kmeans_k{BEST_K}.pkl", "rb") as f:
    km = pickle.load(f)
with open(C.MODELS_DIR / "scaler.pkl", "rb") as f:
    scaler = pickle.load(f)
# Per-day weighting the model was fit in (config.DAY_WEIGHTS). Centroids live in
# WEIGHTED standardized space, so divide by W to undo the weighting BEFORE
# inverse_transform gives back real degrees (mirrors notebook 02).
W = P.feature_weight_vector()
labelled = lab[lab[LABEL_COL] >= 0].copy()
n_lab = int(labelled[LABEL_COL].max()) + 1
cmap = plt.get_cmap("tab20", max(n_lab, 3))

# Centroids in real degrees: [lat50, lon50, lat100, lon100, lat150, lon150] per label.
# (inverse_transform of the standardized k-means centres, via the saved scaler).
raw_cent = P.centroids_to_degrees(km.cluster_centers_ / W, scaler)
if LABEL_COL == "cluster_group" and C.GROUP_MAP:
    _, raw2grp = P.apply_group_map(np.arange(BEST_K), C.GROUP_MAP, BEST_K)
    sizes = lab.loc[lab.cluster_label >= 0, "cluster_label"].value_counts()
    # Merge in the WEIGHTED standardized space (size-weighted mean of the
    # weighted centres), then divide by W and inverse-transform -> a proper
    # group centroid in degrees.
    dim = km.cluster_centers_.shape[1]
    grp_centers = np.zeros((n_lab, dim)); wsum = np.zeros(n_lab)
    for c in range(BEST_K):
        g = raw2grp[c]; w = float(sizes.get(c, 0))
        grp_centers[g] += km.cluster_centers_[c] * w; wsum[g] += w
    grp_centers /= np.where(wsum[:, None] == 0, 1, wsum[:, None])
    disp_cent = P.centroids_to_degrees(grp_centers / W, scaler)
else:
    disp_cent = raw_cent
LABEL_NAMES = C.GROUP_NAMES if LABEL_COL == "cluster_group" else {}
print(f"labelled trajectories: {len(labelled):,} | {LABEL_COL}: {n_lab} labels")
"""),
    md("""
## Figure 1 - Pathway map

Plot up to ~5,000 *full* trajectories per cluster, coloured by label. Full paths
are streamed from the Zarr stores so we never hold everything in memory. We pick
a random set of `trajectory_id`s per cluster, group them by store, and read only
those rows.
"""),
    code("""
import cartopy.crs as ccrs, cartopy.feature as cfeature
rng = np.random.default_rng(C.RANDOM_STATE)

# choose <=5000 trajectory_ids per label (raw cluster or merged group)
pick = (labelled.groupby(LABEL_COL, group_keys=False)
        .apply(lambda d: d.sample(min(5000, len(d)), random_state=C.RANDOM_STATE)))
pick = pick[["trajectory_id", LABEL_COL]].rename(columns={LABEL_COL: "lab"}).copy()
pick["store_index"] = pick.trajectory_id // C.TRAJ_PER_STORE
pick["local"] = pick.trajectory_id % C.TRAJ_PER_STORE
stores = C.list_stores()

fig = plt.figure(figsize=(11, 7))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([C.DOMAIN["lon_min"], C.DOMAIN["lon_max"],
               C.DOMAIN["lat_min"], C.DOMAIN["lat_max"]], crs=ccrs.PlateCarree())
ax.add_feature(cfeature.LAND, facecolor="0.85"); ax.coastlines(lw=.5)

import xarray as xr
for si, grp in pick.groupby("store_index"):
    ds = xr.open_zarr(stores[si])
    loc = grp.local.to_numpy()
    lons = ds.lon.values[loc]; lats = ds.lat.values[loc]
    cl = grp.lab.to_numpy()
    for j in range(len(loc)):
        ax.plot(lons[j], lats[j], color=cmap(cl[j]), lw=.2, alpha=.3,
                transform=ccrs.PlateCarree())
ax.set_title(f"Plume pathways by {LABEL_COL} (k={BEST_K}, {n_lab} labels)")
fig.savefig(C.FIG_DIR / f"pathway_map_k{BEST_K}_{LABEL_COL}.png", dpi=140, bbox_inches="tight")
plt.show()
"""),
    md("## Figure 2 - Seasonal pathway fractions (stacked bars by release month)"),
    code("""
def label_name(c):
    return LABEL_NAMES.get(c, str(c))

def fraction_table(group_col):
    g = labelled.groupby([group_col, LABEL_COL]).size().unstack(fill_value=0)
    return g.div(g.sum(axis=1), axis=0) * 100

seas = fraction_table("release_month").reindex(range(1, 13))
fig, ax = plt.subplots(figsize=(10, 5))
bottom = np.zeros(len(seas))
for c in range(n_lab):
    vals = seas.get(c, pd.Series(0, index=seas.index)).to_numpy()
    ax.bar(seas.index, vals, bottom=bottom, color=cmap(c), label=label_name(c))
    bottom += vals
ax.set_xlabel("release month"); ax.set_ylabel("% of particles")
ax.set_title(f"Seasonal pathway fractions ({LABEL_COL})")
ax.legend(ncol=2, fontsize=7, bbox_to_anchor=(1.01, 1), loc="upper left")
fig.savefig(C.FIG_DIR / f"seasonal_fractions_k{BEST_K}_{LABEL_COL}.png", dpi=130, bbox_inches="tight")
plt.show()
"""),
    md("## Figure 3 - Interannual pathway fractions (stacked area by release year)"),
    code("""
yr = fraction_table("release_year").sort_index()
fig, ax = plt.subplots(figsize=(11, 5))
ax.stackplot(yr.index, *[yr.get(c, pd.Series(0, index=yr.index)).to_numpy()
                         for c in range(n_lab)],
             colors=[cmap(c) for c in range(n_lab)], labels=[label_name(c) for c in range(n_lab)])
ax.set_xlabel("release year"); ax.set_ylabel("% of particles"); ax.set_ylim(0, 100)
ax.set_title(f"Interannual pathway fractions ({LABEL_COL})")
ax.legend(ncol=2, fontsize=7, bbox_to_anchor=(1.01, 1), loc="upper left")
fig.savefig(C.FIG_DIR / f"interannual_fractions_k{BEST_K}_{LABEL_COL}.png", dpi=130, bbox_inches="tight")
plt.show()
"""),
    md("""
## Figure 4 - Transit-time distributions per cluster

Time (days since release) to first reach 10°N, computed from the Zarr stores via
`pipeline.first_crossing_days`. We reuse the per-cluster `pick` sample from
Figure 1 to keep the I/O bounded.
"""),
    code("""
transit = {}   # trajectory_id -> days to 10N
for si, grp in pick.groupby("store_index"):
    days = P.first_crossing_days(stores[si], lat_thresh=10.0)
    for tid, loc in zip(grp.trajectory_id, grp.local):
        transit[tid] = days[loc]
pick["t10N"] = pick.trajectory_id.map(transit)

ncol = 5; nrow = int(np.ceil(n_lab / ncol))
fig, axes = plt.subplots(nrow, ncol, figsize=(3*ncol, 2.4*nrow), squeeze=False)
for c in range(n_lab):
    ax = axes[c // ncol][c % ncol]
    d = pick.loc[pick.lab == c, "t10N"].dropna()
    ax.hist(d, bins=30, color=cmap(c))
    ax.set_title(f"{label_name(c)} (n={len(d)})", fontsize=8)
    ax.set_xlabel("days to 10N", fontsize=7)
for j in range(n_lab, nrow*ncol):
    axes[j // ncol][j % ncol].axis("off")
fig.tight_layout()
fig.savefig(C.FIG_DIR / f"transit_time_histograms_k{BEST_K}_{LABEL_COL}.png", dpi=120)
plt.show()
"""),
    md("## Figure 5 - Centroid positions (marker per sampling day, joined by a line)"),
    code("""
cent = disp_cent   # per label: [lat_d0, lon_d0, lat_d1, lon_d1, ...] real degrees
pct = labelled[LABEL_COL].value_counts(normalize=True).sort_index() * 100
day_markers = ["o", "s", "*", "^", "D", "P"]
day_sizes   = [90, 120, 240, 150, 150, 150]
fig = plt.figure(figsize=(11, 7))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([C.DOMAIN["lon_min"], C.DOMAIN["lon_max"],
               C.DOMAIN["lat_min"], C.DOMAIN["lat_max"]], crs=ccrs.PlateCarree())
ax.add_feature(cfeature.LAND, facecolor="0.85"); ax.coastlines(lw=.5)
for c in range(n_lab):
    lats = cent[c, 0::2]; lons = cent[c, 1::2]      # one entry per day in C.DAYS
    ax.plot(lons, lats, "-", color=cmap(c), lw=1, alpha=.6, transform=ccrs.PlateCarree())
    for j in range(len(C.DAYS)):
        ax.scatter(lons[j], lats[j], color=cmap(c), s=day_sizes[j % len(day_sizes)],
                   marker=day_markers[j % len(day_markers)], edgecolor="k",
                   transform=ccrs.PlateCarree())
    ax.text(lons[-1], lats[-1], f" {label_name(c)} ({pct.get(c,0):.0f}%)", fontsize=8,
            transform=ccrs.PlateCarree())
from matplotlib.lines import Line2D
handles = [Line2D([0], [0], marker=day_markers[j % len(day_markers)], color="k",
                  ls="", mfc="0.7", label=f"day {d}") for j, d in enumerate(C.DAYS)]
ax.legend(handles=handles, loc="lower right", fontsize=8)
ax.set_title(f"Centroids ({LABEL_COL}, k={BEST_K})  days: {list(C.DAYS)}")
fig.savefig(C.FIG_DIR / f"centroids_k{BEST_K}_{LABEL_COL}.png", dpi=140, bbox_inches="tight")
plt.show()
"""),
    md("## Table 1 - Pathway summary"),
    code("""
month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
last_day = C.DAYS[-1]
rows = []
for c in range(n_lab):
    sel = labelled[labelled[LABEL_COL] == c]
    peak = month_names[int(sel.release_month.mode().iloc[0]) - 1] if len(sel) else "-"
    mt = pick.loc[pick.lab == c, "t10N"].dropna()
    rows.append(dict(
        label=c,
        name=LABEL_NAMES.get(c, ""),
        pct=round(len(sel) / len(labelled) * 100, 1),
        peak_month=peak,
        mean_transit_10N=round(float(mt.mean()), 1) if len(mt) else np.nan,
        mean_lat_last=round(float(sel[f"lat_{last_day}"].mean()), 2),
        mean_lon_last=round(float(sel[f"lon_{last_day}"].mean()), 2),
    ))
summary = pd.DataFrame(rows)
summary.to_csv(C.DATA_DIR / f"pathway_summary_k{BEST_K}_{LABEL_COL}.csv", index=False)
print(f"(mean_lat_last / mean_lon_last are the day-{last_day} positions)")
print(summary.to_string(index=False))
"""),
])

print("\nAll notebooks generated.")
