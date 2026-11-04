"""Generate the RADIUS pipeline notebooks with nbformat.

    python build_notebooks.py            # writes every notebook below
    python build_notebooks.py 00 1.5     # only the notebooks whose name starts so

Careful: this OVERWRITES the named notebooks (and any hand edits in them).

Notebooks
---------
00_radius_choice        why RADII_KM = 200 / 500 / 1000 / 1500 / 2000 km (sample of stores)
01_extract_features     Stage 1: every store -> crossing + radius-exit features
02_kmeans_subsample     Stage 2 (optional): K sweep, elbow / silhouette, dendrogram
1.5_Manual_clustering   fit by hand, eyeball the clusters, assign group letters
v2.1.5_Manual_clustering    K sweep for the most distinct, reproducible pathways (to the one-map)
v3.1.5_Manual_clustering    v2 with radius weights ~ r^2 + comparison with v2
v4.1.5_Manual_clustering    v3 + a 750 km radius
explain_direction_balanced_sampling  what the balanced fit sample is (plots of the 15-degree sectors)
1.7_NoCross_clustering      particles that never cross 2.5N (positions at days after release)
1.6_Tropical_subclustering  eastward particles only (direction at GATE_R), own K, by hand
03_assign_labels        Stage 3: label every particle with the 1.5 model
04_diagnostics          Stage 4: maps, fractions, timing, representatives
"""
import sys
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell
from pathlib import Path

NB_DIR = Path(__file__).resolve().parent / "notebooks"
NB_DIR.mkdir(exist_ok=True)
ONLY = sys.argv[1:]


def md(s):
    return new_markdown_cell(s.strip("\n"))


def code(s):
    return new_code_cell(s.strip("\n"))


def params_code(s):
    """Code cell tagged `parameters` (papermill `-p name value` overrides)."""
    c = new_code_cell(s.strip("\n"))
    c.metadata["tags"] = ["parameters"]
    return c


def save(name, cells):
    if ONLY and not any(name.startswith(o) for o in ONLY):
        return
    nb = new_notebook(cells=cells)
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python",
                              "name": "python3"}
    nb.metadata.language_info = {"name": "python"}
    nbf.write(nb, NB_DIR / name)
    print("wrote", NB_DIR / name)


BOOT = r"""
import sys, os
sys.path.insert(0, os.path.abspath(".."))   # project root: config.py, pipeline.py
import numpy as np
import pandas as pd
import config as C
import pipeline as P
print("project root:", C.PROJECT_ROOT)
print(f"crossing: {C.LAT_CROSS} N | radii (km): {C.RADII_KM}")
"""

# Reference lines/box used on the maps of the day-based project (kept so the
# two sets of figures can be compared).
REFS = r"""
import matplotlib.patches as mpatches

def draw_refs(ax, **kw):
    # reference lines from the day-based notebooks + the 2.5N starting line
    for x in (-70, -60, -40):
        ax.axvline(x, lw=.5, **kw)
    ax.axhline(20, lw=.5, **kw)
    ax.axhline(C.LAT_CROSS, lw=.6, ls="--", color="k")
    ax.add_patch(mpatches.Rectangle(xy=(-55, 5), width=10, height=5, lw=1,
                                    edgecolor="green", facecolor="none"))
"""

# =========================================================================== #
# 00 - why these radii
# =========================================================================== #
save("00_radius_choice.ipynb", [
md(r"""
# 00 - Choosing the radii

The clustering starts the clock when a particle first crosses **2.5N** and
describes it by **where it first gets farther than R km from its own crossing
point** (haversine distance), for every R in `config.RADII_KM`. This notebook
shows why those radii were chosen.

It reads a sample of stores (every `STORE_STEP`-th store of each track dir) and
uses the same functions as Stage 1 (`P.first_crossing`,
`P.distance_from_crossing`, `P.first_exit`). Nothing is written to `data/`; the
two figures are saved in `figures/`.

**One particle, step by step:** it crosses 2.5N at 47W. Draw circles of 200,
500, 1000, ... km around that point. Its features are the positions where its
track first leaves each circle. A fast and a slow particle that follow the same
route get the same features - time is not part of the clustering (it is kept
in `days_<R>km` for the diagnostics).
"""),
code(BOOT),
params_code(r"""
STORE_STEP = 60          # every 60th store of each track dir (~28 stores, ~280k particles)
N_SHOW     = 300         # random trajectories drawn on the map
"""),
code(r"""
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs, cartopy.feature as cfeature
from joblib import Parallel, delayed

# --- TUNE ME (also STORE_STEP / N_SHOW above) --------------------------------
CAND_R     = np.union1d(np.arange(100, 4001, 100), C.RADII_KM)   # radii for the curves
N_JOBS     = int(os.environ.get("SLURM_CPUS_PER_TASK", 8))
# -----------------------------------------------------------------------------

stores = []
for d in C.TRACK_DIRS:
    stores += sorted((C.DATA_ROOT / d).glob(C.STORE_GLOB))[::STORE_STEP]
print(len(stores), "stores in the sample")
"""),
md(r"""
## Per-store numbers

For every crossing particle and every candidate radius: the days after the
crossing at which it first gets that far (NaN = never, its track ended first),
and for the chosen radii the compass direction (bearing) from the crossing
point to the exit point. A few whole tracks per store are kept for the map.
"""),
code(r"""
CHOSEN = [int(np.where(CAND_R == r)[0][0]) for r in C.RADII_KM]
n_show_store = int(np.ceil(N_SHOW / len(stores)))

def store_stats(path, seed):
    ds = xr.open_zarr(path)
    lat = ds.lat.values.astype(np.float64)
    lon = ds.lon.values.astype(np.float64)
    time = ds.time.values
    rows = np.arange(lat.shape[0])

    k0, crossed = P.first_crossing(lat)
    dist = P.distance_from_crossing(lat, lon, k0, crossed)
    idx, reached = P.first_exit(dist, CAND_R)
    t_rel = (time - time[rows, k0][:, None]) / np.timedelta64(1, "D")   # days since crossing
    days = np.where(reached, t_rel[rows[:, None], idx], np.nan)

    la0, lo0 = lat[rows, k0], lon[rows, k0]
    ci = idx[:, CHOSEN]
    bear = P.bearing_deg(la0[:, None], lo0[:, None],
                         lat[rows[:, None], ci], lon[rows[:, None], ci])
    bear[~reached[:, CHOSEN]] = np.nan

    rng = np.random.default_rng(seed)
    show = rng.choice(np.where(crossed)[0], n_show_store, replace=False)
    return dict(n=lat.shape[0], days=days[crossed], bear=bear[crossed],
                rmax=np.nanmax(dist[crossed], axis=1),
                show_lat=lat[show], show_lon=lon[show], show_k0=k0[show])

res = Parallel(n_jobs=N_JOBS, backend="loky")(
    delayed(store_stats)(p, i) for i, p in enumerate(stores))

n_all  = sum(r["n"] for r in res)
days   = np.concatenate([r["days"] for r in res])     # (crossers, len(CAND_R))
bear   = np.concatenate([r["bear"] for r in res])     # (crossers, len(RADII_KM))
rmax   = np.concatenate([r["rmax"] for r in res])
n_obs  = max(r["show_lat"].shape[1] for r in res)      # stores hold 740 or 741 outputs
def _pad(a):
    return np.pad(a, ((0, 0), (0, n_obs - a.shape[1])), constant_values=np.nan)
s_lat  = np.concatenate([_pad(r["show_lat"]) for r in res])[:N_SHOW]
s_lon  = np.concatenate([_pad(r["show_lon"]) for r in res])[:N_SHOW]
s_k0   = np.concatenate([r["show_k0"] for r in res])[:N_SHOW]
print(f"{n_all:,} particles, {len(days):,} cross {C.LAT_CROSS}N ({100*len(days)/n_all:.1f}%)")

frac = 100 * (~np.isnan(days)).mean(axis=0)            # % of crossers reaching R
med  = np.nanmedian(days, axis=0)
p10, p90 = np.nanpercentile(days, [10, 90], axis=0)

tab = pd.DataFrame({"reached [%]": frac[CHOSEN],
                    "median days after crossing": med[CHOSEN],
                    "p10": p10[CHOSEN], "p90": p90[CHOSEN]},
                   index=pd.Index(C.RADII_KM, name="radius [km]")).round(1)
print(tab.to_string())
print(f"\nfarthest distance from the crossing point: median {np.median(rmax):.0f} km, "
      f"5-95%: {np.percentile(rmax, 5):.0f}-{np.percentile(rmax, 95):.0f} km")
"""),
md(r"""
## Figure 1 - the circles on a map

**Left:** `N_SHOW` random particles from their crossing onwards, with the
circles drawn around the median crossing point and each particle's exit points
coloured by radius. (In the features every particle uses circles around its
*own* crossing point; one set is drawn here to keep the map readable.)
**Right:** one particle with its own circles; the dashed grey part is before
the crossing, which the clustering ignores.
"""),
code(r"""
pc = ccrs.PlateCarree()
rcol = plt.get_cmap("plasma", len(C.RADII_KM) + 1)
rcolor = {r: rcol(i) for i, r in enumerate(C.RADII_KM)}
ext = [C.DOMAIN["lon_min"], C.DOMAIN["lon_max"], C.DOMAIN["lat_min"], C.DOMAIN["lat_max"]]

def show_exits(la, lo, k0):
    crossed = np.ones(len(k0), bool)
    d = P.distance_from_crossing(la, lo, k0, crossed)
    idx, reached = P.first_exit(d, C.RADII_KM)
    return idx, reached

idx_s, reach_s = show_exits(s_lat, s_lon, s_k0)
lat_c, lon_c = C.LAT_CROSS, float(np.median(s_lon[np.arange(len(s_k0)), s_k0]))

fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), subplot_kw={"projection": pc})
for ax in axes:
    ax.set_extent(ext, crs=pc)
    ax.add_feature(cfeature.LAND, facecolor="0.85", zorder=0); ax.coastlines(lw=.5)
    gl = ax.gridlines(draw_labels=True, lw=.3, color="0.7", alpha=.5)
    gl.top_labels = gl.right_labels = False
    ax.axhline(C.LAT_CROSS, color="k", lw=.7, ls="--")

# (a) many particles, circles around the median crossing point
ax = axes[0]
for i in range(len(s_k0)):
    ax.plot(s_lon[i, s_k0[i]:], s_lat[i, s_k0[i]:], "-", color="0.35", lw=.3,
            alpha=.35, transform=pc)
ax.scatter(s_lon[np.arange(len(s_k0)), s_k0], s_lat[np.arange(len(s_k0)), s_k0],
           s=4, color="k", zorder=4, transform=pc, label="crossing point")
for j, r in enumerate(C.RADII_KM):
    cla, clo = P.circle_latlon(lat_c, lon_c, r)
    ax.plot(clo, cla, "-", color=rcolor[r], lw=1.6, transform=pc, zorder=3)
    ax.text(clo[0], cla[0] + .4, f"{r} km", color=rcolor[r], fontsize=9,
            ha="center", fontweight="bold", transform=pc, zorder=5)
    ok = reach_s[:, j]
    ii = np.where(ok)[0]
    ax.scatter(s_lon[ii, idx_s[ii, j]], s_lat[ii, idx_s[ii, j]], s=7,
               color=rcolor[r], edgecolor="none", zorder=4, transform=pc)
ax.set_title(f"{len(s_k0)} random particles after crossing {C.LAT_CROSS}N; "
             f"dots = where each leaves each circle", fontsize=10)

# (b) one particle with its own circles
ax = axes[1]
rng = np.random.default_rng(C.RANDOM_STATE)
i = int(rng.choice(np.where(reach_s.all(axis=1))[0]))
k0 = s_k0[i]
ax.plot(s_lon[i, :k0 + 1], s_lat[i, :k0 + 1], "--", color="0.5", lw=1, transform=pc,
        label="before crossing (ignored)")
ax.plot(s_lon[i, k0:], s_lat[i, k0:], "-", color="tab:blue", lw=1.2, transform=pc,
        label="after crossing")
ax.scatter(s_lon[i, k0], s_lat[i, k0], s=40, color="k", zorder=5, transform=pc,
           label="crossing point")
for j, r in enumerate(C.RADII_KM):
    cla, clo = P.circle_latlon(s_lat[i, k0], s_lon[i, k0], r)
    ax.plot(clo, cla, "-", color=rcolor[r], lw=1.2, transform=pc)
    k = idx_s[i, j]
    ax.scatter(s_lon[i, k], s_lat[i, k], s=70, color=rcolor[r], edgecolor="k",
               zorder=6, transform=pc)
    ax.annotate(f"{r} km: day {(k - k0) / 4:.0f}", (s_lon[i, k], s_lat[i, k]),
                xytext=(6, 4), textcoords="offset points", fontsize=8,
                color=rcolor[r], fontweight="bold")
ax.legend(loc="lower left", fontsize=8)
ax.set_title("one particle: its features are the 5 exit points "
             "(days after crossing in the labels)", fontsize=10)
fig.tight_layout()
fig.savefig(C.FIG_DIR / "00_radius_choice_map.png", dpi=140, bbox_inches="tight")
plt.show()
"""),
md(r"""
## Figure 2 - how far particles get, how long it takes, and how the exit directions spread

* **Left:** share of crossing particles that ever get R km away. Every run_2
  track stops 185 days after release, and particles cross 2.5N at different
  times, so the larger the radius, the more tracks end first. A particle that
  does not reach a radius gets its last position instead (`partial`) - the
  more of those, the less that radius means.
* **Middle:** days after the crossing to get there (median, 10-90% band).
* **Right:** direction from the crossing point to the exit point at each chosen
  radius (0 = N, -90 = W, 90 = E). A radius where everyone exits in the same
  direction cannot separate pathways; a spread or several peaks can.
"""),
code(r"""
fig, ax = plt.subplots(1, 3, figsize=(17, 4.6))

ax[0].plot(CAND_R, frac, "-", color="0.3")
for n, (j, r) in enumerate(zip(CHOSEN, C.RADII_KM)):
    ax[0].plot(r, frac[j], "o", color=rcolor[r], ms=8, mec="k")
    ax[0].annotate(f"{r} km\n{frac[j]:.1f}%", (r, frac[j]),
                   xytext=(6, 6) if n % 2 else (6, -26),       # alternate so labels don't overlap
                   textcoords="offset points", fontsize=8)
ax[0].set_xlabel("radius around the crossing point [km]")
ax[0].set_ylabel("% of crossing particles that get this far")
ax[0].set_ylim(0, 105); ax[0].grid(color="0.9")

ax[1].fill_between(CAND_R, p10, p90, color="0.85", lw=0, label="10-90%")
ax[1].plot(CAND_R, med, "-", color="0.3", label="median")
for j, r in zip(CHOSEN, C.RADII_KM):
    ax[1].plot(r, med[j], "o", color=rcolor[r], ms=8, mec="k")
ax[1].set_xlabel("radius [km]"); ax[1].set_ylabel("days after crossing to get there")
ax[1].legend(fontsize=8, frameon=False); ax[1].grid(color="0.9")

bins = np.arange(-180, 181, 10)
for j, r in enumerate(C.RADII_KM):
    b = bear[:, j][~np.isnan(bear[:, j])]
    ax[2].hist(b, bins=bins, histtype="step", lw=1.8, color=rcolor[r],
               density=True, label=f"{r} km")
ax[2].set_xticks([-180, -135, -90, -45, 0, 45, 90, 135, 180])
ax[2].set_xticklabels(["S", "SW", "W", "NW", "N", "NE", "E", "SE", "S"])
ax[2].set_xlabel("direction crossing point -> exit point")
ax[2].set_ylabel("density"); ax[2].legend(fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(C.FIG_DIR / "00_radius_choice_stats.png", dpi=140, bbox_inches="tight")
plt.show()
"""),
md(r"""
## Why 200 / 500 / 1000 / 1500 / 2000 km

From the first look at a 28-store sample (2026-10-08); the cells above
recompute these numbers each run:

| radius | reached | median days after crossing | role |
|---|---|---|---|
| 200 km | 99.6% | 9 | gate: almost everyone, still near the NBC |
| 500 km | 99.1% | 15 | early direction (along the shelf vs offshore) |
| 1000 km | 97.5% | 32 | retroflection vs continuing northwest |
| 1500 km | 89.7% | 51 | towards the Antilles vs eastward |
| 2000 km | 73.9% | 73 | destination: about the Lesser Antilles to the NW, ~30W along the retroflection to the E |
| 2500 km | 48.5% | 97 | not used: half the particles would have a filled-in last position |

* **Not every 100 km:** every radius gets the same weight after
  standardization, so many closely spaced small radii would let the near field
  (where pathways have not separated yet) dominate. Check the bearing panel:
  the small radii should be the narrowest.
* **Stop at 2000 km:** beyond it too many tracks end before getting there
  (left panel), and the stand-in last position would be taken at a different
  stage of the journey for each particle.
* **Weights** (`config.RADIUS_WEIGHTS`) start at 1 for every radius and are
  tuned by eye in notebook 1.5, as with the days.
* Particles move away steadily: the farthest distance is close to the distance
  at the end of the track, so "first time past R" is rarely followed by a
  return inside the circle.
"""),
])

# =========================================================================== #
# 01 - extract features
# =========================================================================== #
save("01_extract_features.ipynb", [
md(r"""
# 01 - Extract features  (Stage 1)

For every particle in every store: find its first crossing of `C.LAT_CROSS`,
then the first position farther than each radius in `C.RADII_KM` from its own
crossing point (haversine). One row per particle:

* identity: `store`, `row` (position in the store), `traj` (Parcels ID), and a
  running `trajectory_id` added when the parts are combined;
* `release_*`, `cross_time`, `cross_month`, `cross_year`, `cross_lat/lon`,
  `cross_obs`, `days_to_cross`, `r_last_km` (distance at the track's end);
* per radius R: `lat_<R>km`, `lon_<R>km` (the k-means features) and
  `days_<R>km` (days after crossing; NaN if not reached);
* `status`: `complete` (all radii) / `partial` (gate radius reached, last
  position stands in for the missing radii) / `no_gate` / `no_cross`.

**Output:** `data/features_parts/<store>.parquet` (one per store, restartable)
and `data/features.parquet`.
"""),
code(BOOT),
code(r"""
stores = C.list_stores()
print(f"{len(stores)} stores in {C.TRACK_DIRS}")
print("writing per-store parts to:", C.FEATURE_PARTS_DIR)
stores[:3]
"""),
md(r"""
## 1.1  Sanity check on one store
"""),
code(r"""
df0 = P.extract_store_features(stores[0])
print(df0.status.value_counts().to_string())
# the ID scheme: Parcels IDs have gaps, so traj != row
print("rows 0-4 -> Parcels IDs", df0.traj.head().tolist())
df0.head()
"""),
code(r"""
import matplotlib.pyplot as plt
sub = df0[df0.status == "complete"].head(1000)
fig, ax = plt.subplots(figsize=(7, 5))
ax.scatter(sub.cross_lon, sub.cross_lat, s=4, c="k", label="crossing")
for r in C.RADII_KM:
    ax.scatter(sub[P.lon_col(r)], sub[P.lat_col(r)], s=4, label=f"{r} km")
ax.set_xlabel("lon"); ax.set_ylabel("lat"); ax.legend(markerscale=3)
ax.set_title("store 0: crossing points and exit points")
plt.show()
"""),
md(r"""
## 1.2  All stores (parallel, one process per store)

Parts are named after the store, so re-running only fills the gaps, and a part
always belongs to the store it is named after. `N_JOBS` defaults to
`$SLURM_CPUS_PER_TASK`.
"""),
code(r"""
from joblib import Parallel, delayed

N_JOBS = int(os.environ.get("SLURM_CPUS_PER_TASK", 8))

def _extract_one(s):
    part = C.FEATURE_PARTS_DIR / f"{s.stem}.parquet"
    if part.exists():
        return None
    P.extract_store_features(s).to_parquet(part, index=False)
    return s.stem

print(f"extracting {len(stores)} stores with n_jobs={N_JOBS} ...")
Parallel(n_jobs=N_JOBS, backend="loky", verbose=10)(delayed(_extract_one)(s) for s in stores)
"""),
md(r"""
## 1.3  Combine into `features.parquet`

Only parts of stores that are currently in `C.list_stores()` are used. The
running `trajectory_id` is assigned here; it is a row number for joins and
nothing is decoded from it.
"""),
code(r"""
names = [s.stem for s in stores]
parts = [C.FEATURE_PARTS_DIR / f"{n}.parquet" for n in names]
missing = [p.name for p in parts if not p.exists()]
assert not missing, f"{len(missing)} stores not extracted yet, e.g. {missing[:3]}"
stale = sorted(set(p.stem for p in C.FEATURE_PARTS_DIR.glob("*.parquet")) - set(names))
if stale:
    print(f"ignoring {len(stale)} parts of stores no longer listed, e.g. {stale[:3]}")

features = pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True)
features["store"] = features["store"].astype("category")
features.insert(0, "trajectory_id", np.arange(len(features), dtype=np.int64))
assert not features.duplicated(["store", "traj"]).any(), "duplicate (store, traj)"
features.to_parquet(C.FEATURES_FILE, index=False)
print("combined shape:", features.shape, "->", C.FEATURES_FILE)
"""),
md(r"""
## 1.4  Summary
"""),
code(r"""
n = len(features)
print(f"{n:,} particles from {features.store.nunique()} stores")
for k, v in features.status.value_counts().reindex(P.STATUSES).items():
    print(f"  {k:9s}: {v:12,}  ({100*v/n:5.2f}%)")
cr = features[features.status != "no_cross"]
print(f"\ndays release -> crossing: median {cr.days_to_cross.median():.1f}, "
      f"5-95%: {cr.days_to_cross.quantile(.05):.1f}-{cr.days_to_cross.quantile(.95):.1f}")
print("\nper radius, among crossing particles:")
for r in C.RADII_KM:
    d = cr[P.days_col(r)]
    print(f"  {r:5d} km: reached {100*d.notna().mean():5.1f}%   "
          f"median {d.median():5.1f} d after crossing")
print(f"\nrelease years {features.release_year.min()}-{features.release_year.max()}")
"""),
])

# =========================================================================== #
# 02 - K sweep (optional)
# =========================================================================== #
save("02_kmeans_subsample.ipynb", [
md(r"""
# 02 - K-means on a subsample: K sweep  (Stage 2, optional)

Fits `MiniBatchKMeans` for every K in `C.K_LIST` on `C.N_SUB` `complete`
particles, with the radius features standardized (StandardScaler) and weighted
by `C.RADIUS_WEIGHTS`. Elbow / silhouette, a dendrogram of the centroids, and a
numbered centroid map help choose K for notebook 1.5.

Notebook 1.5 does its own fit; the models written here
(`data/kmeans_models/kmeans_k*.pkl`, `scaler.pkl`) are only for this
comparison and are not used by 03 / 04.
"""),
code(BOOT),
code(r"""
import pickle
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler

features = pd.read_parquet(C.FEATURES_FILE)
complete = features[features.status == "complete"]
sub = complete.sample(n=min(C.N_SUB, len(complete)), random_state=C.RANDOM_STATE)

X_raw  = P.build_feature_matrix(sub)
scaler = StandardScaler().fit(X_raw)
W      = P.feature_weight_vector()
X_sub  = scaler.transform(X_raw) * W
with open(C.MODELS_DIR / "scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)

print(f"complete: {len(complete):,} -> subsample {X_sub.shape}")
print("columns          :", P.feature_columns())
print("std per column   :", np.round(scaler.scale_, 2), "(degrees, before scaling)")
print("radius weights   :", C.RADIUS_WEIGHTS)
"""),
md(r"""
## 2.1  Fit every K
"""),
code(r"""
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
    print(f"k={k:4d}  inertia={km.inertia_:.1f}  silhouette={sil:.3f}  "
          f"sizes[{sizes.min()}..{sizes.max()}]  ({time.time()-t0:.1f}s)")
res = pd.DataFrame(results)
res
"""),
code(r"""
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
a1.plot(res.k, res.inertia, "o-"); a1.set_xlabel("k"); a1.set_ylabel("inertia"); a1.set_title("Elbow")
a2.plot(res.k, res.silhouette, "o-"); a2.set_xlabel("k"); a2.set_ylabel("silhouette")
a2.set_title("Silhouette vs k")
fig.tight_layout(); plt.show()
"""),
md(r"""
## 2.2  Dendrogram of the centroids and a numbered centroid map

Ward clustering of the `INSPECT_K` centroids in the weighted standardized space
(`P.suggest_groups`) gives a first suggestion for merging; the map shows each
centroid from its mean crossing point through the radius exits, numbered at the
outermost radius and haloed in its suggested group colour.
"""),
code(r"""
from scipy.cluster.hierarchy import dendrogram

INSPECT_K = C.K_LIST[0]
N_GROUPS  = 8

with open(C.MODELS_DIR / f"kmeans_k{INSPECT_K}.pkl", "rb") as f:
    km_i = pickle.load(f)
cent_deg = P.centroids_to_degrees(km_i.cluster_centers_ / W, scaler)
lab_i = km_i.predict(X_sub)
start_lon = pd.Series(sub.cross_lon.to_numpy()).groupby(lab_i).mean().reindex(range(INSPECT_K)).to_numpy()
group_map, Z = P.suggest_groups(km_i.cluster_centers_, N_GROUPS)

fig, ax = plt.subplots(figsize=(12, 4))
dendrogram(Z, labels=[str(c) for c in range(INSPECT_K)], ax=ax,
           color_threshold=Z[-(N_GROUPS - 1), 2])
ax.set_title(f"Centroid dendrogram (k={INSPECT_K}); cut -> {N_GROUPS} groups")
ax.set_ylabel("Ward distance (weighted std space)")
plt.show()
print("suggested GROUP_MAP =", group_map)
"""),
code(r"""
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
import cartopy.crs as ccrs, cartopy.feature as cfeature

pc = ccrs.PlateCarree()
cl_cmap  = plt.get_cmap("tab20", INSPECT_K)
grp_ids  = sorted(set(group_map.values()))
grp_cmap = plt.get_cmap("tab10", max(len(grp_ids), 3))
grp_col  = {g: grp_cmap(i) for i, g in enumerate(grp_ids)}

fig = plt.figure(figsize=(11, 8))
ax = plt.axes(projection=pc)
la_all, lo_all = cent_deg[:, 0::2], cent_deg[:, 1::2]
ax.set_extent([min(lo_all.min(), np.nanmin(start_lon)) - 3, lo_all.max() + 3,
               C.LAT_CROSS - 3, la_all.max() + 3], crs=pc)
ax.add_feature(cfeature.LAND, facecolor="0.85"); ax.coastlines(lw=.5)
gl = ax.gridlines(draw_labels=True, lw=.3, color="0.7", alpha=.5)
gl.top_labels = gl.right_labels = False
ax.axhline(C.LAT_CROSS, color="k", lw=.6, ls="--")
for c in range(INSPECT_K):
    lats = np.r_[C.LAT_CROSS, cent_deg[c, 0::2]]
    lons = np.r_[start_lon[c], cent_deg[c, 1::2]]
    ax.plot(lons, lats, ".-", color=cl_cmap(c), lw=1.4, alpha=.8, transform=pc)
    ax.text(lons[-1], lats[-1], str(c), fontsize=10, ha="center", va="center",
            color="white", zorder=4, transform=pc,
            path_effects=[pe.withStroke(linewidth=3, foreground=grp_col[group_map[c]])])
ax.legend(handles=[Line2D([0], [0], marker="o", ls="", mfc=grp_col[g], mec="k",
                          label=f"group {g}") for g in grp_ids], fontsize=8)
ax.set_title(f"Centroids: crossing -> {' -> '.join(f'{r} km' for r in C.RADII_KM)} "
             f"(k={INSPECT_K}); halo = suggested group")
plt.show()
"""),
])

# =========================================================================== #
# 1.5 - manual clustering
# =========================================================================== #
save("1.5_Manual_clustering.ipynb", [
md(r"""
# 1.5 - Manual clustering (tune, eyeball & merge)

Same playground as in the day-based project, on the radius features.

1. Tune `K` and `RADIUS_WEIGHTS` at the top, run top to bottom.
2. Grid: orange = centroid (mean crossing point -> exit at each radius), blue =
   member trajectories after the crossing, grey = before the crossing.
3. Give each cluster a **group letter** in `ASSIGN` (same letter = merged).
4. When happy: set `SAVE_MODEL = True` and re-run the save cell (03 / 04 read
   that model), then paste the printed `GROUP_MAP`, `GROUP_NAMES` and
   `RADIUS_WEIGHTS` into `config.py`.
"""),
code(BOOT + r"""
import xarray as xr
import matplotlib.pyplot as plt
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler

# --- TUNE ME -----------------------------------------------------------------
K = 70
# per-radius weights tuned HERE; paste into config.RADIUS_WEIGHTS when final
RADIUS_WEIGHTS = dict(C.RADIUS_WEIGHTS)      # e.g. {200: 0.5, 500: 1.0, 1000: 1.5, 1500: 1.5, 2000: 2.0}
SAVE_MODEL = False                           # True -> write the fit for notebooks 03 / 04
# -----------------------------------------------------------------------------

W = P.feature_weight_vector(RADIUS_WEIGHTS)
print("radii:", C.RADII_KM, "| K:", K, "| weights:", RADIUS_WEIGHTS)
"""),
md(r"""
## Fit k-means
Standardize each column, apply the radius weights `W`, fit.
"""),
code(r"""
features = pd.read_parquet(C.FEATURES_FILE)
complete = features[features.status == "complete"]
sub = complete.sample(n=min(C.N_SUB, len(complete)),
                      random_state=C.RANDOM_STATE).reset_index(drop=True)

X_raw  = P.build_feature_matrix(sub)
scaler = StandardScaler().fit(X_raw)
X_sub  = scaler.transform(X_raw) * W

km = MiniBatchKMeans(n_clusters=K, random_state=C.RANDOM_STATE,
                     batch_size=10000, n_init=100, max_iter=300)
labels = km.fit_predict(X_sub)
sizes  = np.bincount(labels, minlength=K)

# centroids in degrees [lat_r0, lon_r0, lat_r1, ...]; start = mean crossing point
cent_deg  = P.centroids_to_degrees(km.cluster_centers_ / W, scaler)
start_lon = sub.groupby(labels).cross_lon.mean().reindex(range(K)).to_numpy()
def centroid_track(c):
    return (np.r_[start_lon[c], cent_deg[c, 1::2]],
            np.r_[C.LAT_CROSS, cent_deg[c, 0::2]])
print(f"fit k={K} on {len(sub):,} particles | cluster sizes {sizes.min()}..{sizes.max()}")
"""),
code(r"""
# Persist THIS fit for notebooks 03 / 04 (only when SAVE_MODEL is True).
# The subsample labels keep store / row / traj, so every fitted particle can be
# found again.
import joblib, json
if SAVE_MODEL:
    MODEL_DIR = C.manual_model_dir(K)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(km, MODEL_DIR / f"kmeans_k{K}.pkl")
    joblib.dump(scaler, MODEL_DIR / "scaler.pkl")
    np.save(MODEL_DIR / "weights_W.npy", W)
    np.save(MODEL_DIR / "centroids_deg.npy", cent_deg)
    sub[["trajectory_id", "store", "row", "traj"]].assign(cluster=labels).to_parquet(
        MODEL_DIR / "subsample_labels.parquet", index=False)
    (MODEL_DIR / "fit_metadata.json").write_text(json.dumps(dict(
        source_notebook="1.5_Manual_clustering.ipynb", K=K, LAT_CROSS=C.LAT_CROSS,
        RADII_KM=C.RADII_KM, RADIUS_WEIGHTS={str(k): v for k, v in RADIUS_WEIGHTS.items()},
        N_SUB=C.N_SUB, RANDOM_STATE=C.RANDOM_STATE, n_fitted=int(len(sub)),
        cluster_sizes=sizes.tolist()), indent=2))
    print("saved model ->", MODEL_DIR)
else:
    print("SAVE_MODEL is False -> nothing written")
"""),
md(r"""
## Cheap coastline
Coarsest Natural Earth coastline (110 m) as plain line segments, so each panel
is an ordinary axes (fast).
"""),
code(REFS + r"""
import cartopy.feature as cfeature
lon_lim = (C.DOMAIN["lon_min"], C.DOMAIN["lon_max"])
lat_lim = (C.DOMAIN["lat_min"], C.DOMAIN["lat_max"])

_coast = []
for geom in cfeature.COASTLINE.with_scale("110m").geometries():
    for line in getattr(geom, "geoms", [geom]):
        _coast.append((np.asarray(line.xy[0]), np.asarray(line.xy[1])))

def draw_coast(ax):
    for x, y in _coast:
        ax.plot(x, y, "-", color="0.75", lw=.4, zorder=0)
    ax.set_xlim(*lon_lim); ax.set_ylim(*lat_lim)
print("coastline segments:", len(_coast))
"""),
md(r"""
## All clusters on one map
Every centroid track (crossing -> outermost radius); number at the end.
"""),
code(r"""
fig, ax = plt.subplots(figsize=(9, 7))
draw_coast(ax); draw_refs(ax)
allcmap = plt.get_cmap("tab20", K)
for c in range(K):
    lo, la = centroid_track(c)
    ax.plot(lo, la, "-", color=allcmap(c), lw=1.2, alpha=.8, zorder=2)
    ax.text(lo[-1], la[-1], str(c), fontsize=7, ha="center", va="center", zorder=4)
ax.set_title(f"All {K} centroid tracks (crossing -> {C.RADII_KM[-1]} km)")
fig.tight_layout(); plt.show()
"""),
md(r"""
## Read a few full member trajectories per cluster
`MEMBERS_PER_PANEL` particles per cluster, read by `store` / `row` (checked
against `traj`), each store opened once.
"""),
code(r"""
MEMBERS_PER_PANEL = 12
N_IO_THREADS = int(os.environ.get("SLURM_CPUS_PER_TASK", 16))

memdf = sub[["trajectory_id", "store", "row", "traj", "cross_obs"]].assign(lab=labels)
pick = (memdf.groupby("lab", group_keys=False)
             .apply(lambda d: d.sample(min(MEMBERS_PER_PANEL, len(d)),
                                       random_state=C.RANDOM_STATE)))
paths = P.read_paths(pick, n_jobs=N_IO_THREADS)          # trajectory_id -> (lon, lat)
cross_obs = dict(zip(pick.trajectory_id, pick.cross_obs))
members = {c: pick.loc[pick.lab == c, "trajectory_id"].to_numpy() for c in range(K)}
print(f"read {len(paths):,} full trajectories from {pick.store.nunique()} stores")
"""),
md(r"""
## Assign each cluster a group letter
`ASSIGN[cluster] = "letter"`; same letter => merged. Starts with every cluster
on its own (its number as the label).
"""),
code(r"""
ASSIGN = {c: str(c) for c in range(K)}
# ASSIGN = {
#    0: "A1", 1: "B2", ...
# }
"""),
md(r"""
## The grid - one panel per cluster
"""),
code(r"""
NCOL = 7
LETTER_FRAC = 0.10          # group letter height, as a fraction of the y axis

def draw_cluster(ax, c):
    draw_coast(ax)
    for tid in members[c]:
        lo, la = paths[int(tid)]
        k0 = cross_obs[tid]
        ax.plot(lo[:k0 + 1], la[:k0 + 1], "-", color="0.6", lw=.4, alpha=.4)
        m = ~(np.isnan(lo[k0:]) | np.isnan(la[k0:]))
        ax.plot(lo[k0:][m], la[k0:][m], "-", color="blue", lw=.4, alpha=.3)
    clo, cla = centroid_track(c)
    ax.plot(clo, cla, ".-", color="darkorange", lw=2, zorder=3)

nrow = int(np.ceil(K / NCOL))
fig, axes = plt.subplots(nrow, NCOL, figsize=(2.9 * NCOL, 2.3 * nrow),
                         squeeze=False, sharex=True, sharey=True)
letter_txt = []
for c in range(K):
    ax = axes[c // NCOL][c % NCOL]
    draw_cluster(ax, c); draw_refs(ax)
    ax.set_title(f"cluster {c}  (n={sizes[c]:,})", fontsize=8)
    letter_txt.append((ax, ax.text(0.97, 0.5, ASSIGN[c], transform=ax.transAxes,
                                   ha="right", va="center", fontsize=20,
                                   color="crimson", zorder=6)))
for j in range(K, nrow * NCOL):
    axes[j // NCOL][j % NCOL].axis("off")
fig.suptitle(f"k={K} centroids (orange) + member trajectories "
             f"(blue after / grey before crossing {C.LAT_CROSS}N)", y=1.0)
fig.tight_layout()

fig.canvas.draw()
rend = fig.canvas.get_renderer()
for ax, txt in letter_txt:
    h_ax, h_txt = ax.get_window_extent(rend).height, txt.get_window_extent(rend).height
    txt.set_fontsize(txt.get_fontsize() * (LETTER_FRAC * h_ax / h_txt))
fig.canvas.draw()
# fig.savefig(f"cluster_K{K}_W_{RADIUS_WEIGHTS}.pdf", dpi=130, bbox_inches="tight")
plt.show()
"""),
md(r"""
## Preview the merged groups
One panel per letter with every centroid assigned to it: first coloured by
cluster, then by radius (dark = 200 km, yellow = outermost).
"""),
code(r"""
letters = sorted(set(ASSIGN.values()))
NCOLg = min(4, len(letters))
nrowg = int(np.ceil(len(letters) / NCOLg))
cmap  = plt.get_cmap("tab20", K)

fig, axes = plt.subplots(nrowg, NCOLg, figsize=(3.4 * NCOLg, 2.7 * nrowg),
                         squeeze=False, sharex=True, sharey=True)
for i, L in enumerate(letters):
    ax = axes[i // NCOLg][i % NCOLg]
    draw_coast(ax); draw_refs(ax)
    mem = [c for c in range(K) if ASSIGN[c] == L]
    for c in mem:
        lo, la = centroid_track(c)
        ax.plot(lo, la, "-", color=cmap(c), lw=1.6, zorder=2)
        ax.plot(lo[-1], la[-1], "o", color=cmap(c), mec="k", ms=5, zorder=3)
        off = [(5, 4), (5, -8), (-13, 4), (-13, -8)][mem.index(c) % 4]
        ax.annotate(str(c), (lo[-1], la[-1]), xytext=off, textcoords="offset points",
                    fontsize=6.5, color="0.1", zorder=5)
    ax.set_title(f"group {L}  ({len(mem)} clusters)", fontsize=9)
for j in range(len(letters), nrowg * NCOLg):
    axes[j // NCOLg][j % NCOLg].axis("off")
fig.suptitle("Merged groups (centroids, coloured by cluster)", y=1.0)
fig.tight_layout(); plt.show()
"""),
code(r"""
rcmap = plt.get_cmap("plasma", len(C.RADII_KM) + 1)
rcol  = [rcmap(i) for i in range(len(C.RADII_KM))]

fig, axes = plt.subplots(nrowg, NCOLg, figsize=(3.4 * NCOLg, 2.7 * nrowg),
                         squeeze=False, sharex=True, sharey=True)
for i, L in enumerate(letters):
    ax = axes[i // NCOLg][i % NCOLg]
    draw_coast(ax); draw_refs(ax)
    mem = [c for c in range(K) if ASSIGN[c] == L]
    for c in mem:
        lo, la = centroid_track(c)
        ax.plot(lo, la, "-", color="0.7", lw=1.0, zorder=2)
        ax.scatter(lo[1:], la[1:], c=rcol, s=26, zorder=3, edgecolor="white", linewidths=.5)
        off = [(5, 4), (5, -8), (-13, 4), (-13, -8)][mem.index(c) % 4]
        ax.annotate(str(c), (lo[-1], la[-1]), xytext=off, textcoords="offset points",
                    fontsize=6.5, color="0.1", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=.65))
    ax.set_title(f"group {L}  ({len(mem)} clusters)", fontsize=9)
for j in range(len(letters), nrowg * NCOLg):
    axes[j // NCOLg][j % NCOLg].axis("off")
handles = [plt.Line2D([], [], marker=".", ls="", color=rcol[i], mec="white", ms=7,
                      label=f"{r} km") for i, r in enumerate(C.RADII_KM)]
fig.legend(handles=handles, loc="lower center", ncol=len(C.RADII_KM), frameon=False,
           bbox_to_anchor=(0.5, -0.015))
fig.suptitle("Merged groups (centroids, coloured by radius)", y=1.0)
fig.tight_layout(); plt.show()
"""),
code(r"""
from itertools import combinations
def cdist(a, b):            # distance between two centroid tracks (degrees, all radii)
    return float(np.sqrt(((cent_deg[a] - cent_deg[b]) ** 2).sum()))

print("group  n  max_within_dist(deg)  members")
for L in letters:
    m = [c for c in range(K) if ASSIGN[c] == L]
    spread = max((cdist(a, b) for a, b in combinations(m, 2)), default=0.0)
    flag = "  <-- loose?" if spread > 12 else ""
    print(f"  {L:4s} {len(m):2d}      {spread:6.1f}            {m}{flag}")

print("\nclosest different-label cluster pairs (merge/boundary candidates):")
pairs = sorted((cdist(a, b), a, b) for a, b in combinations(range(K), 2) if ASSIGN[a] != ASSIGN[b])
for d, a, b in pairs[:12]:
    print(f"  {d:5.1f} deg : {a}({ASSIGN[a]})  <->  {b}({ASSIGN[b]})")
"""),
md(r"""
## Distance of every cluster from the `REF_GROUP` centroids
One row per radius (y axis = where the `REF_GROUP` mean centroid exits that
circle); x = how far every other centroid's exit point is from it, in degrees.
Where a line pulls away marks where that pathway stops following `REF_GROUP`.
"""),
code(r"""
REF_GROUP = letters[0]          # any label used in ASSIGN

tracks = cent_deg.reshape(K, len(C.RADII_KM), 2)          # (K, radius, [lat, lon])
ref_members = [c for c in range(K) if ASSIGN[c] == REF_GROUP]
ref = tracks[ref_members].mean(axis=0)
dist = np.sqrt(((tracks - ref) ** 2).sum(axis=2))          # (K, radius) degrees

broad = sorted({ASSIGN[c][0] for c in range(K)})
PAL = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]
color = {L: PAL[i % len(PAL)] for i, L in enumerate(broad)}

def coord(la, lo):
    return f"({abs(la):.1f}{'N' if la >= 0 else 'S'}, {abs(lo):.1f}{'W' if lo < 0 else 'E'})"

rows = np.arange(len(C.RADII_KM))
fig, ax = plt.subplots(figsize=(8, 6))
for c in range(K):
    if c not in ref_members:
        ax.plot(dist[c], rows, "-o", color=color[ASSIGN[c][0]], lw=1.6, ms=4,
                alpha=.75, mec="white", mew=.6, zorder=2)
for c in ref_members:
    ax.plot(dist[c], rows, "--", color="0.45", lw=1.4, zorder=3)
ax.set_yticks(rows)
ax.set_yticklabels([f"{r} km  {coord(la, lo)}" for r, (la, lo) in zip(C.RADII_KM, ref)], fontsize=9)
ax.invert_yaxis()
ax.set_xlabel(f"distance from the {REF_GROUP} exit point at that radius (degrees)")
ax.set_xlim(left=0); ax.xaxis.grid(True, color="0.88", lw=.6); ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for L in broad:
    ax.plot([], [], "-o", color=color[L], lw=1.6, ms=4, label=f"{L}*")
ax.plot([], [], "--", color="0.45", lw=1.4, label=f"{REF_GROUP} (reference)")
ax.legend(loc="upper right", frameon=False, fontsize=8, title="broad group", ncol=2)
ax.set_title(f"Distance of all {K} centroids from {REF_GROUP}", loc="left")
fig.tight_layout(); plt.show()

hdr = "  ".join(f"{r:>6}km" for r in C.RADII_KM)
print(f" clus  grp  {hdr}")
for c in sorted(range(K), key=lambda c: dist[c, -1]):
    print(f" {c:4d}  {ASSIGN[c]:4s} " + "  ".join(f"{v:8.1f}" for v in dist[c]))
"""),
code(r"""
D = np.array([[cdist(a, b) for b in range(K)] for a in range(K)]); np.fill_diagonal(D, np.inf)
bad = [(c, int(D[c].argmin())) for c in range(K) if ASSIGN[c][0] != ASSIGN[int(D[c].argmin())][0]]
print("clusters whose NEAREST neighbour has a different broad letter:")
for c, nn in bad:
    print(f"  {c}({ASSIGN[c]}) -> {nn}({ASSIGN[nn]}) at {D[c, nn]:.1f} deg")
print("none -> broad grouping is clean" if not bad else f"{len(bad)} to check")
"""),
md(r"""
## Export -> paste into `config.py`
"""),
code(r"""
name2id     = {L: i for i, L in enumerate(letters)}
GROUP_MAP   = {c: name2id[ASSIGN[c]] for c in range(K)}
GROUP_NAMES = {i: L for L, i in name2id.items()}

print("RADIUS_WEIGHTS =", RADIUS_WEIGHTS)
print("GROUP_MAP =", GROUP_MAP)
print("GROUP_NAMES =", GROUP_NAMES)
print()
for L in letters:
    print(f"  {L}: {[c for c in range(K) if ASSIGN[c] == L]}")
"""),
])

# =========================================================================== #
# v2.1.5 - choose K: most distinct, reproducible pathways (incl. eastward)
# =========================================================================== #
save("v2.1.5_Manual_clustering.ipynb", [
md(r"""
# v2.1.5 - Manual clustering: choosing K for the most distinct pathways

Version 2 of notebook 1.5, up to "all clusters on one map". It asks: **which K
gives the largest number of pathways that are clearly different from each other
and come back every time** - including the eastward retroflection.

**Why 1.5 found almost only north-west pathways (K=50 gave 1 eastward centroid,
K=150 gave 2):**

1. 1.5 fits on `complete` particles only (reached 2000 km). Eastward particles
   are mostly `partial` (their track ends before 2000 km): only ~7% of them are
   `complete`, so the fit barely sees them.
2. k-means puts clusters where particles are dense. ~86% of particles leave the
   1000 km circle heading north-west, ~3% have any eastward component, so even
   with 150 clusters almost all of them go to the north-west route.

**What this notebook changes:**

* fits on `complete` + `partial` (`FIT_STATUS`);
* **balanced subsample**: particles are drawn with a weight that depends on
  how common their outer direction is (direction crossing point -> 2000 km exit,
  or last position, in 15-degree sectors). `BALANCE_ALPHA = 1` = draw as they
  come (as in 1.5), `0` = every direction sector equally, `0.5` in between.
  Rare routes then get enough particles to get their own clusters. Only the
  *fit* sample is balanced: notebook 03 still labels every particle;
* counts **distinct pathways** for each K: centroid tracks are joined
  (complete linkage) when their mean distance over the radii is below
  `PATHWAY_SEP_KM`, so two pathways are always at least that far apart;
* checks **reproducibility**: the fit is repeated with other random samples
  and seeds; a pathway counts as real if a pathway within `MATCH_KM` appears in
  every other run.

**What the data contain (run_2, checked on the tracks, 2026-10-21):**

* there is **no equatorward pathway** in run_2: after crossing 2.5N, 0.02% of
  particles ever go back south of 2.5N east of 45W and none south of 1N; the
  2.3% that never cross 2.5N are held near the river mouth (1S-2N, 50-47W)
  for the whole 185 days and never go east of 40W;
* the **eastward retroflection exists** but is small: ~0.6% of particles go
  east of 40W south of 10N, ~3% leave the 1000 km circle with an eastward
  component.

**First result (sweep run 2026-10-21, 3 seeds, separation 400 km):**
`BALANCE_ALPHA = 0`, K = 400 gave 23-26 pathways, 96-100% reproduced
(K = 300: 21 in every run; K = 500: no more pathways, less reproducible;
without balancing at most ~18). The cells below recompute this.
"""),
code(BOOT + r"""
import time
import matplotlib.pyplot as plt
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
"""),
params_code(r"""
K_SWEEP = [50, 100, 150, 200, 250, 300, 400, 500]   # K values to try
SEEDS = [42, 1, 7]               # repeated fits (different sample + seed) for reproducibility
BALANCE_ALPHA = 0.0              # 1 as they come, 0 every direction sector equally
PATHWAY_SEP_KM = 400             # two pathways differ if their tracks are >= this far apart (mean over radii)
MATCH_KM = 200                   # a pathway is reproduced if another run has one within this distance
N_SUB = 500_000                  # particles per fit
K = None                         # final K; None -> chosen automatically from the sweep
SAVE_MODEL = False               # True -> write the final fit for notebooks 03 / 04
"""),
code(r"""
FIT_STATUS = ["complete", "partial"]
SECTOR_DEG = 15
RADIUS_WEIGHTS = dict(C.RADIUS_WEIGHTS)      # tune here; paste into config when final
W = P.feature_weight_vector(RADIUS_WEIGHTS)
print("radii:", C.RADII_KM, "| weights:", RADIUS_WEIGHTS, "| balance alpha:", BALANCE_ALPHA,
      "| separation:", PATHWAY_SEP_KM, "km")
"""),
md(r"""
## Particles to fit, and their outer direction
"""),
code(r"""
features = pd.read_parquet(C.FEATURES_FILE)
fitset = features[features.status.isin(FIT_STATUS)].reset_index(drop=True)
del features
R_OUT = C.RADII_KM[-1]
bearing = P.bearing_deg(fitset.cross_lat, fitset.cross_lon,
                        fitset[P.lat_col(R_OUT)], fitset[P.lon_col(R_OUT)])
sector = np.clip(np.floor((bearing + 180) / SECTOR_DEG).astype(int), 0, 360 // SECTOR_DEG - 1)
n_sector = np.bincount(sector, minlength=360 // SECTOR_DEG)
X_all = P.build_feature_matrix(fitset)

tab = pd.DataFrame({"particles": n_sector,
                    "%": (100 * n_sector / n_sector.sum()).round(3)},
                   index=pd.Index([f"{-180 + SECTOR_DEG*i:+4d}..{-180 + SECTOR_DEG*(i+1):+4d}"
                                   for i in range(len(n_sector))], name="direction (deg, 0 N, -90 W)"))
print(f"{len(fitset):,} particles ({', '.join(FIT_STATUS)})")
print(tab[tab.particles > 0].to_string())

def balanced_sample(seed):
    rng = np.random.default_rng(seed)
    w = n_sector[sector].astype(float) ** (BALANCE_ALPHA - 1.0)
    return rng.choice(len(fitset), size=min(N_SUB, len(fitset)), replace=False, p=w / w.sum())

idx0 = balanced_sample(SEEDS[0])
print(f"\nshare with an eastward outer direction: all {100*(bearing > 0).mean():.1f}%, "
      f"in a balanced sample {100*(bearing[idx0] > 0).mean():.1f}%")
"""),
md(r"""
## Helpers: fit, centroids in degrees, distinct pathways
Centroids in degrees are the mean member position per radius. Track distance =
mean haversine distance between two centroids' exit points over the radii.
"""),
code(r"""
def track_dist(A, B):
    nr = A.shape[1] // 2
    D = 0
    for j in range(nr):
        D = D + P.haversine_km(A[:, None, 2*j], A[:, None, 2*j+1], B[None, :, 2*j], B[None, :, 2*j+1])
    return D / nr

def fit_k(k, idx, seed, n_init=10):
    X = X_all[idx]
    sc = StandardScaler().fit(X)
    km = MiniBatchKMeans(n_clusters=k, random_state=seed, batch_size=10000,
                         n_init=n_init, max_iter=300).fit(sc.transform(X) * W)
    cent = pd.DataFrame(X).groupby(km.labels_).mean().reindex(range(k)).to_numpy()
    return km, sc, cent

def pathways(cent):
    # flat groups of centroids; every pair of groups is >= PATHWAY_SEP_KM apart
    Z = linkage(squareform(track_dist(cent, cent), checks=False), "complete")
    g = fcluster(Z, t=PATHWAY_SEP_KM, criterion="distance") - 1
    return g, np.array([cent[g == i].mean(axis=0) for i in range(g.max() + 1)])

def is_east(tracks, start_lon):
    return P.bearing_deg(C.LAT_CROSS, start_lon, tracks[:, -2], tracks[:, -1]) > 0
"""),
md(r"""
## Sweep K: number of distinct pathways and their reproducibility
For every K and seed: fit, group the centroids into pathways, count them (and
the eastward ones), and check whether each pathway reappears in the other runs.
"""),
code(r"""
start_all = fitset.cross_lon.to_numpy()
rows, runs = [], {}
for k in K_SWEEP:
    for seed in SEEDS:
        t0 = time.time()
        idx = balanced_sample(seed)
        km_s, sc_s, cent = fit_k(k, idx, seed)
        g, ptrack = pathways(cent)
        slon = pd.Series(start_all[idx]).groupby(km_s.labels_).mean().reindex(range(k)).to_numpy()
        pstart = np.array([slon[g == i].mean() for i in range(g.max() + 1)])
        runs[(k, seed)] = ptrack
        rows.append(dict(K=k, seed=seed, pathways=len(ptrack),
                         east=int(is_east(ptrack, pstart).sum()), sec=round(time.time() - t0)))
    for seed in SEEDS:                       # reproducibility of each run's pathways
        others = [runs[(k, s)] for s in SEEDS if s != seed]
        ok = np.all([track_dist(runs[(k, seed)], o).min(axis=1) < MATCH_KM for o in others], axis=0)
        next(r for r in rows if r["K"] == k and r["seed"] == seed)["reproduced_%"] = round(100 * ok.mean())
    print(f"K={k:4d}: " + ", ".join(f"{r['pathways']} ({r['east']} east, {r['reproduced_%']}%)"
                                     for r in rows if r["K"] == k), flush=True)
sweep = pd.DataFrame(rows)
summary = sweep.groupby("K")[["pathways", "east", "reproduced_%"]].agg(["mean", "min", "max"]).round(1)
summary
"""),
code(r"""
s = sweep.groupby("K").agg(p=("pathways", "mean"), pmin=("pathways", "min"), pmax=("pathways", "max"),
                           e=("east", "mean"), r=("reproduced_%", "mean"))
fig, ax = plt.subplots(1, 2, figsize=(13, 4))
ax[0].fill_between(s.index, s.pmin, s.pmax, color="0.85", lw=0, label="min-max over seeds")
ax[0].plot(s.index, s.p, "o-", color="k", label="all pathways")
ax[0].plot(s.index, s.e, "s-", color="tab:red", label="eastward pathways")
ax[0].set_xlabel("K"); ax[0].set_ylabel(f"pathways >= {PATHWAY_SEP_KM} km apart")
ax[0].legend(frameon=False); ax[0].grid(color="0.92")
ax[1].plot(s.index, s.r, "o-", color="tab:blue")
ax[1].axhline(95, color="0.5", ls="--", lw=.8)
ax[1].set_xlabel("K"); ax[1].set_ylabel("% of pathways found in every other run")
ax[1].set_ylim(50, 102); ax[1].grid(color="0.92")
fig.suptitle(f"balance alpha {BALANCE_ALPHA}, fit on {', '.join(FIT_STATUS)}"); fig.tight_layout(); plt.show()

# choice: most pathways among the K whose pathways are >= 95% reproduced (smaller K on ties)
good = s[s.r >= 95]
K_AUTO = int((good if len(good) else s).sort_values(["p", "r"], ascending=[False, False]).index[0])
print(f"suggested K = {K_AUTO}: {s.loc[K_AUTO, 'p']:.1f} pathways "
      f"({s.loc[K_AUTO, 'e']:.1f} eastward), {s.loc[K_AUTO, 'r']:.0f}% reproduced")
if K is None:
    K = K_AUTO
print("K used below:", K)
"""),
md(r"""
## Final fit at K
Same balanced sample as the first seed, more initialisations. The pathway of
each cluster (`PATH_OF`) and the share of ALL particles in each pathway (from
labelling a random 2 million) are what the next steps of 1.5 build on.
"""),
code(r"""
idx = balanced_sample(SEEDS[0])
sub = fitset.iloc[idx].reset_index(drop=True)
km, scaler, cent_deg = fit_k(K, idx, SEEDS[0], n_init=20)
labels = km.labels_
sizes = np.bincount(labels, minlength=K)
start_lon = sub.groupby(labels).cross_lon.mean().reindex(range(K)).to_numpy()
def centroid_track(c):
    return (np.r_[start_lon[c], cent_deg[c, 1::2]],
            np.r_[C.LAT_CROSS, cent_deg[c, 0::2]])

PATH_OF, ptrack = pathways(cent_deg)
n_path = len(ptrack)
pstart = np.array([start_lon[PATH_OF == i].mean() for i in range(n_path)])
p_east = is_east(ptrack, pstart)

ps = np.random.default_rng(0).choice(len(fitset), size=min(2_000_000, len(fitset)), replace=False)
lab_ps = km.predict(scaler.transform(X_all[ps]) * W)
share = 100 * np.bincount(PATH_OF[lab_ps], minlength=n_path) / len(ps)
cl_count = np.bincount(lab_ps, minlength=K)          # real particles per cluster (in the 2M sample)
ptab = pd.DataFrame({"clusters": np.bincount(PATH_OF, minlength=n_path),
                     "% of all particles": share.round(3), "eastward": p_east,
                     f"exit lat {R_OUT}km": ptrack[:, -2].round(1),
                     f"exit lon {R_OUT}km": ptrack[:, -1].round(1)})
ptab.index.name = "pathway"
print(f"fit K={K} on {len(sub):,} particles (balanced) | {n_path} pathways, "
      f"{int(p_east.sum())} eastward | cluster sizes {sizes.min()}..{sizes.max()}")
ptab.sort_values("% of all particles", ascending=False)
"""),
code(r"""
# Persist THIS fit for notebooks 03 / 04 (only when SAVE_MODEL is True).
import joblib, json
if SAVE_MODEL:
    MODEL_DIR = C.manual_model_dir(K)
    if MODEL_DIR.exists():
        print("NOTE: overwriting", MODEL_DIR)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(km, MODEL_DIR / f"kmeans_k{K}.pkl")
    joblib.dump(scaler, MODEL_DIR / "scaler.pkl")
    np.save(MODEL_DIR / "weights_W.npy", W)
    np.save(MODEL_DIR / "centroids_deg.npy", cent_deg)
    np.save(MODEL_DIR / "pathway_of_cluster.npy", PATH_OF)
    sub[["trajectory_id", "store", "row", "traj"]].assign(cluster=labels).to_parquet(
        MODEL_DIR / "subsample_labels.parquet", index=False)
    sweep.to_csv(MODEL_DIR / "k_sweep.csv", index=False)
    (MODEL_DIR / "fit_metadata.json").write_text(json.dumps(dict(
        source_notebook="v2.1.5_Manual_clustering.ipynb", K=K, LAT_CROSS=C.LAT_CROSS,
        RADII_KM=C.RADII_KM, RADIUS_WEIGHTS={str(k): v for k, v in RADIUS_WEIGHTS.items()},
        FIT_STATUS=FIT_STATUS, BALANCE_ALPHA=BALANCE_ALPHA, SECTOR_DEG=SECTOR_DEG,
        PATHWAY_SEP_KM=PATHWAY_SEP_KM, n_pathways=int(n_path), N_SUB=N_SUB,
        seed=SEEDS[0], n_fitted=int(len(sub)), cluster_sizes=sizes.tolist()), indent=2))
    print("saved model ->", MODEL_DIR)
else:
    print("SAVE_MODEL is False -> nothing written")
"""),
md(r"""
## Cheap coastline
"""),
code(REFS + r"""
import cartopy.feature as cfeature
lon_lim = (C.DOMAIN["lon_min"], C.DOMAIN["lon_max"])
lat_lim = (C.DOMAIN["lat_min"], C.DOMAIN["lat_max"])
_coast = []
for geom in cfeature.COASTLINE.with_scale("110m").geometries():
    for line in getattr(geom, "geoms", [geom]):
        _coast.append((np.asarray(line.xy[0]), np.asarray(line.xy[1])))
def draw_coast(ax):
    for x, y in _coast:
        ax.plot(x, y, "-", color="0.75", lw=.4, zorder=0)
    ax.set_xlim(*lon_lim); ax.set_ylim(*lat_lim)
"""),
md(r"""
## All clusters on one map
Top left: every centroid track, coloured by its pathway. The other three
panels draw one line per pathway in three ways (label = pathway number and its
share of all particles; line width ~ share; red = eastward):

* **plain mean** of the pathway's centroids (every cluster counts the same);
* **size-weighted mean**: each centroid weighted by how many real particles
  it gets when a random 2 million particles are labelled, so big clusters
  count more (the fit sample was balanced, so cluster sizes in the fit do not
  show how common a route is);
* **representative cluster**: the real centroid of the pathway whose track is
  closest, on average, to all the others in it - a track that some cluster
  actually has, not an average of several.

Zigzags in the eastward lines come from particles whose track ends before
1500 / 2000 km: their "exit" there is the last position, which can lie inside
the circle.
"""),
code(r"""
def mean_tracks(weights):
    tr, st = [], []
    for i in range(n_path):
        m = PATH_OF == i
        w = weights[m] if weights[m].sum() > 0 else np.ones(m.sum())
        tr.append(np.average(cent_deg[m], axis=0, weights=w))
        st.append(np.average(start_lon[m], weights=w))
    return np.array(tr), np.array(st)

def representative_tracks():
    tr, st, rep = [], [], []
    for i in range(n_path):
        mem = np.where(PATH_OF == i)[0]
        D = track_dist(cent_deg[mem], cent_deg[mem])
        c = mem[D.mean(axis=1).argmin()]        # closest on average to the other members
        tr.append(cent_deg[c]); st.append(start_lon[c]); rep.append(c)
    return np.array(tr), np.array(st), np.array(rep)

tr_plain, st_plain = mean_tracks(np.ones(K))
tr_wmean, st_wmean = mean_tracks(cl_count.astype(float))
tr_rep, st_rep, REP_OF = representative_tracks()

pcmap = plt.get_cmap("tab20", max(n_path, 3))
la_all = np.r_[cent_deg[:, 0::2].ravel(), C.LAT_CROSS]; lo_all = cent_deg[:, 1::2].ravel()
zoom = (lo_all.min() - 3, lo_all.max() + 3, min(la_all.min(), 0) - 2, la_all.max() + 3)

def draw_pathways(ax, tracks, starts, title):
    draw_coast(ax); draw_refs(ax)
    for i in range(n_path):
        lo = np.r_[starts[i], tracks[i, 1::2]]; la = np.r_[C.LAT_CROSS, tracks[i, 0::2]]
        ax.plot(lo, la, ".-", color="tab:red" if p_east[i] else pcmap(i),
                lw=1 + 3 * np.sqrt(share[i] / share.max()), zorder=3)
        ax.text(lo[-1], la[-1], f" {i} ({share[i]:.2g}%)", fontsize=7, zorder=4)
    ax.set_title(title)

fig, axes = plt.subplots(2, 2, figsize=(18, 15), sharex=True, sharey=True)
ax = axes[0, 0]
draw_coast(ax); draw_refs(ax)
for c in range(K):
    lo, la = centroid_track(c)
    ax.plot(lo, la, "-", color=pcmap(PATH_OF[c]), lw=.8, alpha=.7, zorder=2)
ax.set_title(f"All {K} centroid tracks, coloured by pathway ({n_path} pathways "
             f">= {PATHWAY_SEP_KM} km apart)")
draw_pathways(axes[0, 1], tr_plain, st_plain, "Pathways: plain mean of their centroids")
draw_pathways(axes[1, 0], tr_wmean, st_wmean, "Pathways: mean weighted by real particles per cluster")
draw_pathways(axes[1, 1], tr_rep, st_rep, "Pathways: representative cluster (a real centroid)")
for a in axes.ravel():
    a.set_xlim(zoom[0], zoom[1]); a.set_ylim(zoom[2], zoom[3])
fig.tight_layout(); plt.show()

# how far apart the three versions are, per pathway (mean over radii, km)
diff = pd.DataFrame({
    "% of particles": share.round(3), "clusters": np.bincount(PATH_OF, minlength=n_path),
    "representative cluster": REP_OF,
    "plain vs weighted [km]": np.diag(track_dist(tr_plain, tr_wmean)).round(0),
    "plain vs representative [km]": np.diag(track_dist(tr_plain, tr_rep)).round(0),
    "weighted vs representative [km]": np.diag(track_dist(tr_wmean, tr_rep)).round(0)},
    index=pd.Index(range(n_path), name="pathway"))
diff.sort_values("% of particles", ascending=False)
"""),
])

# =========================================================================== #
# v3.1.5 - v2 + radius weights ~ r^2 (from the radius/weight experiments)
# =========================================================================== #
save("v3.1.5_Manual_clustering.ipynb", [
md(r"""
# v3.1.5 - Manual clustering with radius weights ~ radius²

Same method as **v2.1.5** (fit on `complete` + `partial`, direction-balanced
sample, K sweep with 3 seeds, pathways >= 400 km apart that reappear in every
run), with the radius weights chosen by the experiments below. The K sweep is
run for **both** the new weights and the v2 weights (same samples and seeds),
so the two can be compared directly here.

## What the experiments did (2026-10-21)

Question: which radii and which weights give the most pathways that are far
apart and go in **different directions** (out of different sides of the NBC
box 55-45W / 5-10N, eastward / low-latitude retroflection), with the fewest
clusters.

* **Test sample:** every 5th store (308 stores, 3.1 M particles), features at
  13 radii 50 ... 2000 km (`data/experiments/features_dense.parquet`).
* **58 set-ups**: 5 radius sets (current 200-2000 km; fine start 50/100/200/
  500/1000/2000; 9 radii 50 ... 2000; 8 log-spaced 50 ... 2000; all 13) x 5
  weightings (equal, near radii heavier, far radii heavier, both ends, by the
  gap between radii), your v2 weights, 24 random weightings and steeper ramps.
* **Same yardstick for all:** pathway distances are always measured at the
  200 / 500 / 1000 / 1500 / 2000 km points, whatever radii were clustered.
* **Ranked by** sides of the NBC box the pathways leave through, eastward
  pathways, eastward ones ending south of 8N, all pathways (K = 50-500,
  3 seeds, reproducible pathways only).

**Results** (means over 3 seeds, reproducible pathways):

| weights at 200 / 500 / 1000 / 1500 / 2000 km | smallest K that matches v2 at K=400 | K=400: eastward / all | K=500: eastward / all |
|---|---|---|---|
| v2 (1.5 / 2 / 1 / 1.5 / 1) | 400 | 9 / 18 | 10 / 21 |
| **~ radius² (0.03 / 0.17 / 0.66 / 1.5 / 2.65)** | **150** | **11 / 24** | **14 / 28** |

* adding 50 / 100 km radii never helped; weighting the near radii more was
  worst for every radius set (near the crossing all water is in the same NBC);
* more weight on the far radii helps up to ~radius²; radius³ / radius⁴ and
  dropping the 200 / 500 km radii were worse;
* fair check: radius^1.5 and radius² ramps were also run on the fine-start and
  dense radius sets. The ramp improves every set (e.g. 9 radii 50 ... 2000 km:
  7.7 -> 9.2 eastward pathways), but the current set stays best: 19.2 pathways
  and it matches v2 at K=400 already at K=150 (other sets: K=200-300);
* every set-up uses the N, W and E sides of the box; none has a pathway
  leaving through the S side - after crossing 2.5N the water does not go back
  toward the equator in run_2.

**Box for the exit sides (2026-10-21):** on the real tracks of up to 500
members per pathway, 4.6% of all particles leave the NBC box through one side
and later through another (mostly N → E, W → E: retroflection that first heads
north or west) and 4.7% wiggle out and back in through the same side. The box
used here (`NBC_BOX`) is the NBC box with its west side moved out to 56.2W
and its north side to 11N: 56.2-45W / 5-11N. Tests of other boxes: `data/experiments/box_margin_test*.py`.

The K sweep is saved (`data/experiments/v3_k_sweep.csv`); with `RUN_SWEEP = False`
it is loaded instead of recomputed, so the notebook runs in a few minutes.

Scripts and full table: `data/experiments/` (`eval_configs.py`,
`summarize.py`, `final_ranking.txt`); map: `figures/radius_weight_comparison.png`.
"""),
code(BOOT + r"""
import time
import matplotlib.pyplot as plt
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
"""),
params_code(r"""
K_SWEEP = [50, 100, 150, 200, 250, 300, 400, 500]   # K values to try
# radius weights ~ radius^2 (best in the experiments) and the v2 weights to compare with
RADIUS_WEIGHTS = {200: 0.027, 500: 0.166, 1000: 0.663, 1500: 1.492, 2000: 2.653}
COMPARE_WEIGHTS = {200: 1.5, 500: 2, 1000: 1.0, 1500: 1.5, 2000: 1}
RUN_COMPARISON = True            # also sweep the v2 weights (doubles the sweep time)
RUN_SWEEP = False                # False: load the saved sweep (data/experiments/v3_k_sweep.csv); True: recompute (~25 min)
# box used to classify how pathways leave the NBC region (lon0, lon1, lat0, lat1)
# = (west, east, south, north). The NBC box is 55-45W / 5-10N; its west side is
# moved out to 56.2W and its north side to 11N; east (45W) and south (5N) are the
# original NBC box.
NBC_BOX = (-56.2, -45.0, 5.0, 11.0)
SEEDS = [42, 1, 7]               # repeated fits (different sample + seed) for reproducibility
BALANCE_ALPHA = 0.0              # 1 as they come, 0 every direction sector equally
PATHWAY_SEP_KM = 400             # two pathways differ if their tracks are >= this far apart (mean over radii)
MATCH_KM = 200                   # a pathway is reproduced if another run has one within this distance
N_SUB = 500_000                  # particles per fit
K = None                         # final K; None -> chosen automatically from the sweep
SAVE_MODEL = False               # True -> write the final fit for notebooks 03 / 04
"""),
code(r"""
FIT_STATUS = ["complete", "partial"]
SECTOR_DEG = 15
W = P.feature_weight_vector(RADIUS_WEIGHTS)
W_CMP = P.feature_weight_vector(COMPARE_WEIGHTS)
print("radii:", C.RADII_KM, "| weights:", RADIUS_WEIGHTS, "| v2 weights:", COMPARE_WEIGHTS,
      "| balance alpha:", BALANCE_ALPHA,
      "| separation:", PATHWAY_SEP_KM, "km")
"""),
md(r"""
## Particles to fit, and their outer direction
"""),
code(r"""
features = pd.read_parquet(C.FEATURES_FILE)
fitset = features[features.status.isin(FIT_STATUS)].reset_index(drop=True)
del features
R_OUT = C.RADII_KM[-1]
bearing = P.bearing_deg(fitset.cross_lat, fitset.cross_lon,
                        fitset[P.lat_col(R_OUT)], fitset[P.lon_col(R_OUT)])
sector = np.clip(np.floor((bearing + 180) / SECTOR_DEG).astype(int), 0, 360 // SECTOR_DEG - 1)
n_sector = np.bincount(sector, minlength=360 // SECTOR_DEG)
X_all = P.build_feature_matrix(fitset)

tab = pd.DataFrame({"particles": n_sector,
                    "%": (100 * n_sector / n_sector.sum()).round(3)},
                   index=pd.Index([f"{-180 + SECTOR_DEG*i:+4d}..{-180 + SECTOR_DEG*(i+1):+4d}"
                                   for i in range(len(n_sector))], name="direction (deg, 0 N, -90 W)"))
print(f"{len(fitset):,} particles ({', '.join(FIT_STATUS)})")
print(tab[tab.particles > 0].to_string())

def balanced_sample(seed):
    rng = np.random.default_rng(seed)
    w = n_sector[sector].astype(float) ** (BALANCE_ALPHA - 1.0)
    return rng.choice(len(fitset), size=min(N_SUB, len(fitset)), replace=False, p=w / w.sum())

idx0 = balanced_sample(SEEDS[0])
print(f"\nshare with an eastward outer direction: all {100*(bearing > 0).mean():.1f}%, "
      f"in a balanced sample {100*(bearing[idx0] > 0).mean():.1f}%")
"""),
md(r"""
## Helpers: fit, centroids in degrees, distinct pathways
Centroids in degrees are the mean member position per radius. Track distance =
mean haversine distance between two centroids' exit points over the radii.
"""),
code(r"""
def track_dist(A, B):
    nr = A.shape[1] // 2
    D = 0
    for j in range(nr):
        D = D + P.haversine_km(A[:, None, 2*j], A[:, None, 2*j+1], B[None, :, 2*j], B[None, :, 2*j+1])
    return D / nr

def fit_k(k, idx, seed, n_init=10, Wv=None):
    Wv = W if Wv is None else Wv
    X = X_all[idx]
    sc = StandardScaler().fit(X)
    km = MiniBatchKMeans(n_clusters=k, random_state=seed, batch_size=10000,
                         n_init=n_init, max_iter=300).fit(sc.transform(X) * Wv)
    cent = pd.DataFrame(X).groupby(km.labels_).mean().reindex(range(k)).to_numpy()
    return km, sc, cent

def pathways(cent):
    # flat groups of centroids; every pair of groups is >= PATHWAY_SEP_KM apart
    Z = linkage(squareform(track_dist(cent, cent), checks=False), "complete")
    g = fcluster(Z, t=PATHWAY_SEP_KM, criterion="distance") - 1
    return g, np.array([cent[g == i].mean(axis=0) for i in range(g.max() + 1)])

def is_east(tracks, start_lon):
    return P.bearing_deg(C.LAT_CROSS, start_lon, tracks[:, -2], tracks[:, -1]) > 0

BOX = dict(lon0=NBC_BOX[0], lon1=NBC_BOX[1], lat0=NBC_BOX[2], lat1=NBC_BOX[3])   # grouping box
def _inside(lo, la):
    return BOX["lon0"] <= lo <= BOX["lon1"] and BOX["lat0"] <= la <= BOX["lat1"]

def exit_face(lons, lats):
    # side of the NBC box (N, W, E, S) through which a track first leaves it after
    # entering; 'none' = never inside, 'stays' = still inside at its last point
    was_in = False
    for k in range(len(lons) - 1):
        p, q = (lons[k], lats[k]), (lons[k + 1], lats[k + 1])
        if _inside(*p):
            was_in = True
            if not _inside(*q):
                dx, dy, ts = q[0] - p[0], q[1] - p[1], {}
                if dy > 0: ts["N"] = (BOX["lat1"] - p[1]) / dy
                if dy < 0: ts["S"] = (BOX["lat0"] - p[1]) / dy
                if dx < 0: ts["W"] = (BOX["lon0"] - p[0]) / dx
                if dx > 0: ts["E"] = (BOX["lon1"] - p[0]) / dx
                return min(ts, key=ts.get)
        elif not was_in:
            if _inside(*q):
                was_in = True
            else:                                   # segment may cross the whole box
                for t in np.linspace(0, 1, 50)[1:-1]:
                    x, y = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
                    if _inside(x, y):
                        sub_t = np.linspace(t, 1, 50)
                        return exit_face(list(p[0] + sub_t * (q[0] - p[0])),
                                         list(p[1] + sub_t * (q[1] - p[1])))
    return "stays" if was_in else "none"

def faces(tracks, starts):
    return [exit_face(list(np.r_[starts[i], tracks[i, 1::2]]), list(np.r_[C.LAT_CROSS, tracks[i, 0::2]]))
            for i in range(len(tracks))]

# one colour per exit side of the grouping box, used by every pathway map
FACE_COL = {"N": "tab:blue", "W": "tab:green", "E": "tab:red", "S": "tab:purple", "none": "0.5", "stays": "k"}
"""),
md(r"""
## Sweep K: number of distinct pathways and their reproducibility
For every K and seed: fit, group the centroids into pathways, count them (and
the eastward ones), and check whether each pathway reappears in the other runs.
"""),
code(r"""
start_all = fitset.cross_lon.to_numpy()

def run_sweep(Wv, label):
    rows, runs = [], {}
    for k in K_SWEEP:
        for seed in SEEDS:
            idx = balanced_sample(seed)
            km_s, sc_s, cent = fit_k(k, idx, seed, Wv=Wv)
            g, ptrack_s = pathways(cent)
            slon = pd.Series(start_all[idx]).groupby(km_s.labels_).mean().reindex(range(k)).to_numpy()
            pstart_s = np.array([slon[g == i].mean() for i in range(g.max() + 1)])
            fc = faces(ptrack_s, pstart_s)
            runs[(k, seed)] = ptrack_s
            rows.append(dict(weights=label, K=k, seed=seed, pathways=len(ptrack_s),
                             east=int(is_east(ptrack_s, pstart_s).sum()),
                             **{f"exit_{f}": fc.count(f) for f in ("N", "W", "E", "S")}))
        for seed in SEEDS:                   # reproducibility of each run's pathways
            others = [runs[(k, s)] for s in SEEDS if s != seed]
            ok = np.all([track_dist(runs[(k, seed)], o).min(axis=1) < MATCH_KM for o in others], axis=0)
            next(r for r in rows if r["K"] == k and r["seed"] == seed)["reproduced_%"] = round(100 * ok.mean())
        print(f"[{label}] K={k:4d}: " + ", ".join(
            f"{r['pathways']} ({r['east']} east, {r['reproduced_%']}%)" for r in rows if r["K"] == k), flush=True)
    return pd.DataFrame(rows)

SWEEP_CACHE = C.DATA_DIR / "experiments" / "v3_k_sweep.csv"
if RUN_SWEEP or not SWEEP_CACHE.exists():
    sweep = run_sweep(W, "r2")
    sweep_cmp = run_sweep(W_CMP, "v2") if RUN_COMPARISON else None
    pd.concat([sweep, sweep_cmp]).to_csv(SWEEP_CACHE, index=False)
else:
    _all = pd.read_csv(SWEEP_CACHE)
    sweep = _all[_all.weights == "r2"].reset_index(drop=True)
    sweep_cmp = _all[_all.weights == "v2"].reset_index(drop=True) if RUN_COMPARISON else None
    print("loaded saved sweep:", SWEEP_CACHE, "(set RUN_SWEEP = True to recompute)")
cols = [c for c in ["pathways", "east", "exit_N", "exit_W", "exit_E", "exit_S", "reproduced_%"] if c in sweep]
pd.concat([sweep, sweep_cmp]).groupby(["weights", "K"])[cols].mean().round(1)
"""),
code(r"""
def agg(sw):
    sw = sw.assign(rp=sw.pathways * sw["reproduced_%"] / 100)   # reproducible pathways per run
    return sw.groupby("K").agg(p=("pathways", "mean"), pmin=("pathways", "min"), pmax=("pathways", "max"),
                               e=("east", "mean"), r=("reproduced_%", "mean"),
                               rp=("rp", "mean"), rpmin=("rp", "min"), rpmax=("rp", "max"))
s = agg(sweep)
fig, ax = plt.subplots(1, 2, figsize=(13, 4))
ax[0].fill_between(s.index, s.pmin, s.pmax, color="0.85", lw=0, label="min-max over seeds (r²)")
ax[0].plot(s.index, s.p, "o-", color="k", label="all pathways, weights ~ r²")
ax[0].plot(s.index, s.e, "s-", color="tab:red", label="eastward, weights ~ r²")
ax[1].fill_between(s.index, s.rpmin, s.rpmax, color="lightblue", alpha=.5, lw=0, label="min-max over seeds (r²)")
ax[1].plot(s.index, s.rp, "o-", color="tab:blue", label="weights ~ r²")
if sweep_cmp is not None:
    sc_ = agg(sweep_cmp)
    ax[0].plot(sc_.index, sc_.p, "o--", color="0.5", label="all pathways, v2 weights")
    ax[0].plot(sc_.index, sc_.e, "s--", color="salmon", label="eastward, v2 weights")
    ax[1].plot(sc_.index, sc_.rp, "o--", color="slategray", label="v2 weights")
ax[0].set_xlabel("K"); ax[0].set_ylabel(f"pathways >= {PATHWAY_SEP_KM} km apart")
ax[0].legend(frameon=False, fontsize=8); ax[0].grid(color="0.92")
ax[1].legend(frameon=False, fontsize=8)
ax[1].set_xlabel("K"); ax[1].set_ylabel("reproducible pathways (found in every other run)")
ax[1].grid(color="0.92")
fig.suptitle(f"balance alpha {BALANCE_ALPHA}, fit on {', '.join(FIT_STATUS)}"); fig.tight_layout(); plt.show()

# choice: most pathways among the K whose pathways are >= 95% reproduced (smaller K on ties)
good = s[s.r >= 95]
K_AUTO = int((good if len(good) else s).sort_values(["p", "r"], ascending=[False, False]).index[0])
print(f"suggested K = {K_AUTO}: {s.loc[K_AUTO, 'p']:.1f} pathways "
      f"({s.loc[K_AUTO, 'e']:.1f} eastward), {s.loc[K_AUTO, 'r']:.0f}% reproduced "
      f"= {s.loc[K_AUTO, 'rp']:.1f} reproducible pathways")
_tab = s[["p", "rp", "r", "e"]].rename(columns={"p": "pathways", "rp": "reproducible", "r": "% reproduced", "e": "eastward"})
if sweep_cmp is not None:
    _tab = pd.concat({"weights ~ r²": _tab, "v2 weights": sc_[["p", "rp", "r", "e"]].rename(
        columns={"p": "pathways", "rp": "reproducible", "r": "% reproduced", "e": "eastward"})}, axis=1)
print(_tab.round(1).to_string())
if sweep_cmp is not None:
    ref = sc_.loc[400] if 400 in sc_.index else sc_.iloc[-1]
    match = s[(s.p >= ref.p) & (s.e >= ref.e)]
    print(f"v2 weights at K={int(ref.name)}: {ref.p:.1f} pathways ({ref.e:.1f} eastward); "
          f"weights ~ r² reach that from K = {int(match.index.min()) if len(match) else 'none of the K tried'}")
if K is None:
    K = K_AUTO
print("K used below:", K)
"""),
md(r"""
## Final fit at K
Same balanced sample as the first seed, more initialisations. The pathway of
each cluster (`PATH_OF`) and the share of ALL particles in each pathway (from
labelling a random 2 million) are what the next steps of 1.5 build on.
"""),
code(r"""
idx = balanced_sample(SEEDS[0])
sub = fitset.iloc[idx].reset_index(drop=True)
km, scaler, cent_deg = fit_k(K, idx, SEEDS[0], n_init=20)
labels = km.labels_
sizes = np.bincount(labels, minlength=K)
start_lon = sub.groupby(labels).cross_lon.mean().reindex(range(K)).to_numpy()
def centroid_track(c):
    return (np.r_[start_lon[c], cent_deg[c, 1::2]],
            np.r_[C.LAT_CROSS, cent_deg[c, 0::2]])

PATH_OF, ptrack = pathways(cent_deg)
n_path = len(ptrack)
pstart = np.array([start_lon[PATH_OF == i].mean() for i in range(n_path)])
p_east = is_east(ptrack, pstart)
p_face = np.array(faces(ptrack, pstart))

ps = np.random.default_rng(0).choice(len(fitset), size=min(2_000_000, len(fitset)), replace=False)
lab_ps = km.predict(scaler.transform(X_all[ps]) * W)
share = 100 * np.bincount(PATH_OF[lab_ps], minlength=n_path) / len(ps)
cl_count = np.bincount(lab_ps, minlength=K)          # real particles per cluster (in the 2M sample)
ptab = pd.DataFrame({"clusters": np.bincount(PATH_OF, minlength=n_path),
                     "% of all particles": share.round(3), "eastward": p_east,
                     "leaves NBC box via": p_face,
                     f"exit lat {R_OUT}km": ptrack[:, -2].round(1),
                     f"exit lon {R_OUT}km": ptrack[:, -1].round(1)})
ptab.index.name = "pathway"
print(f"fit K={K} on {len(sub):,} particles (balanced) | {n_path} pathways, "
      f"{int(p_east.sum())} eastward | cluster sizes {sizes.min()}..{sizes.max()}")
print("pathways by NBC-box exit side:", pd.Series(p_face).value_counts().to_dict())
ptab.sort_values("% of all particles", ascending=False)
"""),
code(r"""
# Persist THIS fit for notebooks 03 / 04 (only when SAVE_MODEL is True).
import joblib, json
if SAVE_MODEL:
    MODEL_DIR = C.manual_model_dir(K)
    if MODEL_DIR.exists():
        print("NOTE: overwriting", MODEL_DIR)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(km, MODEL_DIR / f"kmeans_k{K}.pkl")
    joblib.dump(scaler, MODEL_DIR / "scaler.pkl")
    np.save(MODEL_DIR / "weights_W.npy", W)
    np.save(MODEL_DIR / "centroids_deg.npy", cent_deg)
    np.save(MODEL_DIR / "pathway_of_cluster.npy", PATH_OF)
    sub[["trajectory_id", "store", "row", "traj"]].assign(cluster=labels).to_parquet(
        MODEL_DIR / "subsample_labels.parquet", index=False)
    pd.concat([sweep, sweep_cmp]).to_csv(MODEL_DIR / "k_sweep.csv", index=False)
    (MODEL_DIR / "fit_metadata.json").write_text(json.dumps(dict(
        source_notebook="v3.1.5_Manual_clustering.ipynb", K=K, LAT_CROSS=C.LAT_CROSS,
        RADII_KM=C.RADII_KM, RADIUS_WEIGHTS={str(k): v for k, v in RADIUS_WEIGHTS.items()},
        FIT_STATUS=FIT_STATUS, BALANCE_ALPHA=BALANCE_ALPHA, SECTOR_DEG=SECTOR_DEG,
        PATHWAY_SEP_KM=PATHWAY_SEP_KM, n_pathways=int(n_path), N_SUB=N_SUB,
        seed=SEEDS[0], n_fitted=int(len(sub)), cluster_sizes=sizes.tolist()), indent=2))
    print("saved model ->", MODEL_DIR)
else:
    print("SAVE_MODEL is False -> nothing written")
"""),
md(r"""
## Cheap coastline
"""),
code(REFS + r"""
_draw_refs_base = draw_refs
def draw_refs(ax, **kw):
    # reference lines + the grouping box (dashed) on top of the NBC box (green)
    _draw_refs_base(ax, **kw)
    ax.add_patch(mpatches.Rectangle((BOX["lon0"], BOX["lat0"]), BOX["lon1"] - BOX["lon0"],
                                    BOX["lat1"] - BOX["lat0"], fill=False, ec="darkgreen",
                                    ls="--", lw=1.2, zorder=1))
import cartopy.feature as cfeature
lon_lim = (C.DOMAIN["lon_min"], C.DOMAIN["lon_max"])
lat_lim = (C.DOMAIN["lat_min"], C.DOMAIN["lat_max"])
_coast = []
for geom in cfeature.COASTLINE.with_scale("110m").geometries():
    for line in getattr(geom, "geoms", [geom]):
        _coast.append((np.asarray(line.xy[0]), np.asarray(line.xy[1])))
def draw_coast(ax):
    for x, y in _coast:
        ax.plot(x, y, "-", color="0.75", lw=.4, zorder=0)
    ax.set_xlim(*lon_lim); ax.set_ylim(*lat_lim)
"""),
md(r"""
## All clusters on one map
Top left: every centroid track, coloured by its pathway (one colour per pathway). The other three
panels draw one line per pathway in three ways (label = pathway number and its
share of all particles; line width ~ share). In these three panels every line is
coloured by the side of the grouping box (`NBC_BOX`, dashed) it leaves through: N blue, W green, E red,
S purple, stays inside black, never enters grey:

* **plain mean** of the pathway's centroids (every cluster counts the same);
* **size-weighted mean**: each centroid weighted by how many real particles
  it gets when a random 2 million particles are labelled, so big clusters
  count more (the fit sample was balanced, so cluster sizes in the fit do not
  show how common a route is);
* **representative cluster**: the real centroid of the pathway whose track is
  closest, on average, to all the others in it - a track that some cluster
  actually has, not an average of several.

Zigzags in the eastward lines come from particles whose track ends before
1500 / 2000 km: their "exit" there is the last position, which can lie inside
the circle.
"""),
code(r"""
def mean_tracks(weights):
    tr, st = [], []
    for i in range(n_path):
        m = PATH_OF == i
        w = weights[m] if weights[m].sum() > 0 else np.ones(m.sum())
        tr.append(np.average(cent_deg[m], axis=0, weights=w))
        st.append(np.average(start_lon[m], weights=w))
    return np.array(tr), np.array(st)

def representative_tracks():
    tr, st, rep = [], [], []
    for i in range(n_path):
        mem = np.where(PATH_OF == i)[0]
        D = track_dist(cent_deg[mem], cent_deg[mem])
        c = mem[D.mean(axis=1).argmin()]        # closest on average to the other members
        tr.append(cent_deg[c]); st.append(start_lon[c]); rep.append(c)
    return np.array(tr), np.array(st), np.array(rep)

tr_plain, st_plain = mean_tracks(np.ones(K))
tr_wmean, st_wmean = mean_tracks(cl_count.astype(float))
tr_rep, st_rep, REP_OF = representative_tracks()

pcmap = plt.get_cmap("tab20", max(n_path, 3))
la_all = np.r_[cent_deg[:, 0::2].ravel(), C.LAT_CROSS]; lo_all = cent_deg[:, 1::2].ravel()
zoom = (lo_all.min() - 3, lo_all.max() + 3, min(la_all.min(), 0) - 2, la_all.max() + 3)

def face_legend(ax, used):
    ax.legend(handles=[plt.Line2D([], [], color=c, lw=2, label=k) for k, c in FACE_COL.items() if k in used],
              title="leaves the box via", frameon=False, loc="lower right")

def draw_pathways(ax, tracks, starts, title):
    # each pathway coloured by the side of the grouping box its drawn track leaves through
    draw_coast(ax); draw_refs(ax)
    fc = faces(tracks, starts)
    for i in range(n_path):
        lo = np.r_[starts[i], tracks[i, 1::2]]; la = np.r_[C.LAT_CROSS, tracks[i, 0::2]]
        ax.plot(lo, la, ".-", color=FACE_COL[fc[i]],
                lw=1 + 3 * np.sqrt(share[i] / share.max()), zorder=3)
        ax.text(lo[-1], la[-1], f" {i} ({share[i]:.2g}%)", fontsize=7, zorder=4)
    face_legend(ax, set(fc))
    ax.set_title(title)

fig, axes = plt.subplots(2, 2, figsize=(18, 15), sharex=True, sharey=True)
ax = axes[0, 0]
draw_coast(ax); draw_refs(ax)
for c in range(K):
    lo, la = centroid_track(c)
    ax.plot(lo, la, "-", color=pcmap(PATH_OF[c]), lw=.8, alpha=.7, zorder=2)
ax.set_title(f"All {K} centroid tracks, coloured by pathway ({n_path} pathways "
             f">= {PATHWAY_SEP_KM} km apart)")
draw_pathways(axes[0, 1], tr_plain, st_plain, "Pathways: plain mean of their centroids")
draw_pathways(axes[1, 0], tr_wmean, st_wmean, "Pathways: mean weighted by real particles per cluster")
draw_pathways(axes[1, 1], tr_rep, st_rep, "Pathways: representative cluster (a real centroid)")
for a in axes.ravel():
    a.set_xlim(zoom[0], zoom[1]); a.set_ylim(zoom[2], zoom[3])
fig.tight_layout(); plt.show()

# how far apart the three versions are, per pathway (mean over radii, km)
diff = pd.DataFrame({
    "% of particles": share.round(3), "clusters": np.bincount(PATH_OF, minlength=n_path),
    "representative cluster": REP_OF,
    "plain vs weighted [km]": np.diag(track_dist(tr_plain, tr_wmean)).round(0),
    "plain vs representative [km]": np.diag(track_dist(tr_plain, tr_rep)).round(0),
    "weighted vs representative [km]": np.diag(track_dist(tr_wmean, tr_rep)).round(0)},
    index=pd.Index(range(n_path), name="pathway"))
diff.sort_values("% of particles", ascending=False)
"""),
md(r"""
## Pathways by how they leave the NBC box
Representative cluster of each pathway (the tracks drawn here are also the
ones classified). Green box = NBC box 55-45W / 5-10N.

* **Left:** coloured by the first side the pathway leaves the box through.
* **Right:** pathways that leave the box **two or more times** - they exit,
  come back in, and exit again - coloured by the order of the sides, e.g.
  `N → E` = out through the north side, back in, out through the east side.
  Pathways that leave only once are grey.

The track is followed in small steps along each straight piece between the
points at 2.5N, 200, 500, 1000, 1500 and 2000 km, so a crossing between two
points is not missed.
"""),
code(r"""
def box_sequence(lons, lats, n_sub=200):
    # every exit from (and entry into) the NBC box along the track, in order
    lo = np.concatenate([np.linspace(lons[k], lons[k + 1], n_sub, endpoint=False) for k in range(len(lons) - 1)] + [[lons[-1]]])
    la = np.concatenate([np.linspace(lats[k], lats[k + 1], n_sub, endpoint=False) for k in range(len(lats) - 1)] + [[lats[-1]]])
    ins = (lo >= BOX["lon0"]) & (lo <= BOX["lon1"]) & (la >= BOX["lat0"]) & (la <= BOX["lat1"])
    def side(x, y):              # side of the box a point just outside it lies beyond
        d = {"N": y - BOX["lat1"], "S": BOX["lat0"] - y, "W": BOX["lon0"] - x, "E": x - BOX["lon1"]}
        return max(d, key=d.get)
    exits, entries = [], []
    for k in range(len(ins) - 1):
        if ins[k] and not ins[k + 1]:
            exits.append(side(lo[k + 1], la[k + 1]))
        elif not ins[k] and ins[k + 1]:
            entries.append(side(lo[k], la[k]))
    return exits, entries, bool(ins[-1])

def seq_label(exits, ends_inside):
    if not exits:
        return "stays" if ends_inside else "none"
    lab = " → ".join(exits)
    return lab + " (ends inside)" if ends_inside else lab

seq = [box_sequence(np.r_[st_rep[i], tr_rep[i, 1::2]], np.r_[C.LAT_CROSS, tr_rep[i, 0::2]]) for i in range(n_path)]
first_exit = np.array([ex[0] if ex else ("stays" if end else "none") for ex, _, end in seq])
n_exits = np.array([len(ex) for ex, _, _ in seq])
seq_lab = np.array([seq_label(ex, end) for ex, _, end in seq])

bt = pd.DataFrame({"% of particles": share.round(3), "first exit": first_exit, "times it leaves": n_exits,
                   "exit sequence": seq_lab, "enters through": [" → ".join(en) for _, en, _ in seq]},
                  index=pd.Index(range(n_path), name="pathway"))
print("first exit side:", pd.Series(first_exit).value_counts().to_dict())
print("leave the box 2+ times:", int((n_exits >= 2).sum()), "pathways,",
      f"{share[n_exits >= 2].sum():.3f}% of particles;",
      pd.Series(seq_lab[n_exits >= 2]).value_counts().to_dict())

multi = sorted(set(seq_lab[n_exits >= 2]))
mcmap = plt.get_cmap("tab10", max(len(multi), 3))
SEQ_COL = {L: mcmap(i) for i, L in enumerate(multi)}

fig, axes = plt.subplots(1, 2, figsize=(22, 8.5), sharex=True, sharey=True)
for ax in axes:
    draw_coast(ax); draw_refs(ax)
    ax.set_xlim(zoom[0], zoom[1]); ax.set_ylim(zoom[2], zoom[3])
for i in range(n_path):
    lo = np.r_[st_rep[i], tr_rep[i, 1::2]]; la = np.r_[C.LAT_CROSS, tr_rep[i, 0::2]]
    lw = 1 + 3 * np.sqrt(share[i] / share.max())
    axes[0].plot(lo, la, ".-", color=FACE_COL[first_exit[i]], lw=lw, zorder=3)
    axes[0].text(lo[-1], la[-1], f" {i} ({share[i]:.2g}%)", fontsize=7, zorder=4)
    if n_exits[i] >= 2:
        axes[1].plot(lo, la, ".-", color=SEQ_COL[seq_lab[i]], lw=max(lw, 2), zorder=4)
        axes[1].text(lo[-1], la[-1], f" {i} ({share[i]:.2g}%)", fontsize=7, zorder=5)
    else:
        axes[1].plot(lo, la, "-", color="0.8", lw=.8, zorder=2)
axes[0].legend(handles=[plt.Line2D([], [], color=c, lw=2, label=k) for k, c in FACE_COL.items()
                        if k in set(first_exit)], title="first exit side", frameon=False, loc="lower right")
axes[0].set_title(f"K={K}: {n_path} pathways by first exit side: " + ", ".join(
    f"{k} {v}" for k, v in pd.Series(first_exit).value_counts().items()))
axes[1].legend(handles=[plt.Line2D([], [], color=c, lw=2, label=k) for k, c in SEQ_COL.items()]
               + [plt.Line2D([], [], color="0.8", lw=1, label="leaves once")],
               title="exit sequence (out, back in, out ...)", frameon=False, loc="lower right")
axes[1].set_title(f"Pathways that leave the box 2+ times: {int((n_exits >= 2).sum())} "
                  f"({share[n_exits >= 2].sum():.2g}% of particles)")
fig.tight_layout(); plt.show()
bt.sort_values(["times it leaves", "% of particles"], ascending=False)
"""),
md(r"""
## Hierarchical view: how the clusters group into pathways
The pathways above are made by **complete-linkage** clustering of the centroid
tracks (distance = mean distance between their points at 200 ... 2000 km),
cut at `PATHWAY_SEP_KM`. The dendrograms show that tree:

* **left:** all K centroids (only the top of the tree, the last merges, is
  drawn); dashed line = the cut, every branch below it is one pathway;
* **right:** the pathways themselves (representative tracks), labelled with
  pathway number, first exit side of the grouping box and share of particles -
  pathways that join low in this tree are the closest candidates to merge by
  hand.
"""),
code(r"""
from scipy.cluster.hierarchy import dendrogram
Z_cl = linkage(squareform(track_dist(cent_deg, cent_deg), checks=False), "complete")
Z_pw = linkage(squareform(track_dist(tr_rep, tr_rep), checks=False), "complete")
fig, ax = plt.subplots(1, 2, figsize=(20, 6.5), gridspec_kw={"width_ratios": [1.1, 1]})
dendrogram(Z_cl, ax=ax[0], truncate_mode="lastp", p=min(3 * n_path, K), color_threshold=PATHWAY_SEP_KM,
           show_leaf_counts=True, leaf_rotation=90, leaf_font_size=7)
ax[0].axhline(PATHWAY_SEP_KM, color="k", ls="--", lw=.8)
ax[0].set_ylabel("complete-linkage distance (km)")
ax[0].set_title(f"{K} centroids -> {n_path} pathways (cut at {PATHWAY_SEP_KM} km); leaves = groups of clusters (count)")
labels = [f"{i} {first_exit[i]} {share[i]:.2g}%" for i in range(n_path)]
dn = dendrogram(Z_pw, ax=ax[1], labels=labels, leaf_rotation=90, leaf_font_size=8,
                color_threshold=0, above_threshold_color="0.4")
for t in ax[1].get_xticklabels():
    t.set_color(FACE_COL[t.get_text().split()[1]])
ax[1].set_ylabel("complete-linkage distance (km)")
ax[1].set_title("pathways (representative tracks): number, first exit side, % of particles")
fig.tight_layout(); plt.show()
"""),
md(r"""
## Hierarchical grouping of the clusters, on the map
The K centroid tracks are grouped by **complete-linkage** hierarchical
clustering (distance = mean distance between their points at 200 ... 2000 km,
the same distance as for the pathways) and the tree is cut into `N_GROUPS`
groups. Thin lines = centroid tracks coloured by group; thick line = the
group's mean track weighted by its real particles, labelled with group number
and share of all particles. Each panel is one cut, so going from left to
right shows which clusters split off first.
"""),
code(r"""
N_GROUPS = [4, 8, 12]           # cuts of the tree to show (one panel each)
import matplotlib.patheffects as pe
# Z_cl = the centroid tree of the left dendrogram above
fig, axes = plt.subplots(1, len(N_GROUPS), figsize=(9 * len(N_GROUPS), 8), sharex=True, sharey=True,
                         squeeze=False)
HGROUP = {}
for ax, ng in zip(axes[0], N_GROUPS):
    hg = fcluster(Z_cl, t=ng, criterion="maxclust") - 1
    HGROUP[ng] = hg
    gcmap = plt.get_cmap("tab10" if hg.max() < 10 else "tab20", max(hg.max() + 1, 3))
    draw_coast(ax); draw_refs(ax)
    for c in range(K):
        lo, la = centroid_track(c)
        ax.plot(lo, la, "-", color=gcmap(hg[c]), lw=.6, alpha=.45, zorder=2)
    for gi in range(hg.max() + 1):
        mem = hg == gi
        wts = cl_count[mem] if cl_count[mem].sum() > 0 else np.ones(mem.sum())
        tr = np.average(cent_deg[mem], axis=0, weights=wts)
        st = np.average(start_lon[mem], weights=wts)
        lo = np.r_[st, tr[1::2]]; la = np.r_[C.LAT_CROSS, tr[0::2]]
        g_share = 100 * cl_count[mem].sum() / cl_count.sum()
        ax.plot(lo, la, ".-", color=gcmap(gi), lw=4, zorder=4,
                path_effects=[pe.withStroke(linewidth=6, foreground="k")])
        ax.text(lo[-1], la[-1], f" {gi} ({g_share:.2g}%, {mem.sum()} cl)", fontsize=8, zorder=5,
                fontweight="bold", color=gcmap(gi))
    ax.set_xlim(zoom[0], zoom[1]); ax.set_ylim(zoom[2], zoom[3])
    ax.set_title(f"{K} clusters cut into {hg.max() + 1} hierarchical groups")
fig.tight_layout(); plt.show()

# which pathways (>= PATHWAY_SEP_KM apart) end up in which group, per cut
pd.DataFrame({f"group ({ng} groups)": [sorted(set(HGROUP[ng][PATH_OF == i])) for i in range(n_path)]
              for ng in N_GROUPS} | {"% of particles": share.round(3), "first exit": first_exit},
             index=pd.Index(range(n_path), name="pathway")).sort_values("% of particles", ascending=False)
"""),
md(r"""
## Hierarchical groups versus real trajectories
For the 8- and 12-group cuts above: one panel per group with real particle
tracks after the 2.5N crossing.

* **blue** = particles of the **fit sample** (the balanced 500,000 k-means was
  trained on) that fall in the group;
* **green** = particles **not** in the fit sample - k-means never saw them,
  they are only assigned to their nearest centroid. If a group is real, the
  green tracks follow the blue ones;
* **orange** = the group's mean track (weighted by real particles).

Title: group number, its share of all particles, and how many fit / non-fit
particles it has.
"""),
code(r"""
REAL_CUTS = [8, 12]              # which cuts of the tree to show (any number of groups)
MEMBERS_PER_GROUP = 25           # tracks of each kind (blue / green) per panel
N_IO_THREADS = int(os.environ.get("SLURM_CPUS_PER_TASK", 16))
for ng in REAL_CUTS:             # cuts not drawn on the map above are cut from the same tree here
    if ng not in HGROUP:
        HGROUP[ng] = fcluster(Z_cl, t=ng, criterion="maxclust") - 1

trained = np.zeros(len(fitset), dtype=bool); trained[idx] = True
nf = np.where(~trained)[0]                                   # rows of fitset not in the fit sample
lab_fit = km.labels_                                         # cluster of each fit-sample particle (order of idx)
lab_nf = km.predict(scaler.transform(X_all[nf]) * W)         # cluster of each non-fit particle
cols = ["trajectory_id", "store", "row", "traj", "cross_obs"]
picks = []
for ng in REAL_CUTS:
    hg = HGROUP[ng]
    for kind, rows_, labs in (("fit", idx, lab_fit), ("nonfit", nf, lab_nf)):
        d = fitset.iloc[rows_][cols].assign(group=hg[labs], kind=kind, cut=ng)
        picks.append(pd.concat([g.sample(min(MEMBERS_PER_GROUP, len(g)), random_state=C.RANDOM_STATE)
                                for _, g in d.groupby("group")]))
pick_all = pd.concat(picks, ignore_index=True)
gpaths = P.read_paths(pick_all.drop_duplicates("trajectory_id"), n_jobs=N_IO_THREADS)
print(f"read {len(gpaths):,} real tracks; {len(nf):,} non-fit particles labelled")

for ng in REAL_CUTS:
    hg = HGROUP[ng]
    n_fit = np.bincount(hg[lab_fit], minlength=hg.max() + 1)
    n_nf = np.bincount(hg[lab_nf], minlength=hg.max() + 1)
    ncol = 4; nrow = int(np.ceil((hg.max() + 1) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.6 * ncol, 3.6 * nrow), squeeze=False, sharex=True, sharey=True)
    for gi in range(hg.max() + 1):
        ax = axes[gi // ncol][gi % ncol]
        draw_coast(ax); draw_refs(ax)
        sel = pick_all[(pick_all.cut == ng) & (pick_all.group == gi)]
        for kind, col in (("nonfit", "green"), ("fit", "blue")):
            for tid, k0 in sel.loc[sel.kind == kind, ["trajectory_id", "cross_obs"]].itertuples(index=False):
                lo, la = gpaths[int(tid)]
                m = ~(np.isnan(lo[k0:]) | np.isnan(la[k0:]))
                ax.plot(lo[k0:][m], la[k0:][m], "-", color=col, lw=.5, alpha=.35, zorder=2)
        mem = hg == gi
        wts = cl_count[mem] if cl_count[mem].sum() > 0 else np.ones(mem.sum())
        tr = np.average(cent_deg[mem], axis=0, weights=wts); st = np.average(start_lon[mem], weights=wts)
        ax.plot(np.r_[st, tr[1::2]], np.r_[C.LAT_CROSS, tr[0::2]], ".-", color="darkorange", lw=2.5, zorder=4)
        ax.set_xlim(zoom[0], zoom[1]); ax.set_ylim(zoom[2], zoom[3])
        g_share = 100 * cl_count[mem].sum() / cl_count.sum()
        ax.set_title(f"group {gi}: {g_share:.2g}% of particles\nfit {n_fit[gi]:,} | non-fit {n_nf[gi]:,}", fontsize=9)
    for j in range(hg.max() + 1, nrow * ncol):
        axes[j // ncol][j % ncol].axis("off")
    fig.suptitle(f"{ng} hierarchical groups: blue = fit sample, green = not in the fit sample, "
                 f"orange = group mean track", y=1.0)
    fig.tight_layout(); plt.show()
"""),
md(r"""
## Cross-check: the K = 20 fit of `1.5_Manual_clustering_dirBalance_sampling` versus the hierarchical groups
The K = 20 model of that notebook was not saved, so it is refitted here
**exactly as there** (complete + partial, direction-balanced sample with
alpha = 0 and seed `C.RANDOM_STATE`, weights from `config.RADIUS_WEIGHTS`,
`n_init = 100`, `random_state = C.RANDOM_STATE`) - same sample, same settings,
so the same 20 clusters (compare the printed cluster sizes with that notebook).

Both models then label the same 2 million real particles, and the table shows,
for every K = 20 cluster, how its particles are spread over the hierarchical
groups of the K = 400 fit. A K = 20 cluster that falls almost entirely into one
group means the two methods agree on that route; one that splits over several
groups is where they disagree.
"""),
code(r"""
CROSS_CUTS = [12, 8]             # hierarchical cuts to compare with (the first one gets the heatmap)
K20 = 20
for ng in CROSS_CUTS:            # cuts not drawn on the map above are cut from the same tree here
    if ng not in HGROUP:
        HGROUP[ng] = fcluster(Z_cl, t=ng, criterion="maxclust") - 1

# --- refit the K = 20 model of 1.5_Manual_clustering_dirBalance_sampling (same sample, same settings)
W20 = P.feature_weight_vector(C.RADIUS_WEIGHTS)
X20 = X_all[idx]                                   # idx = the same balanced sample (alpha 0, seed 42)
sc20 = StandardScaler().fit(X20)
km20 = MiniBatchKMeans(n_clusters=K20, random_state=C.RANDOM_STATE, batch_size=10000,
                       n_init=100, max_iter=300).fit(sc20.transform(X20) * W20)
sz20 = np.bincount(km20.labels_, minlength=K20)
print(f"K=20 refit: cluster sizes {sz20.min():,}..{sz20.max():,} "
      f"(1.5_Manual_clustering_dirBalance_sampling printed 8177..64645)")
print("weights:", C.RADIUS_WEIGHTS)

# --- both models label the same 2 M real particles (ps, lab_ps from the final-fit cell)
lab20 = km20.predict(sc20.transform(X_all[ps]) * W20)
share20 = 100 * np.bincount(lab20, minlength=K20) / len(ps)

summary = {}
for j, ng in enumerate(CROSS_CUTS):
    grp = HGROUP[ng][lab_ps]                                  # hierarchical group of each particle
    ct = pd.crosstab(lab20, grp)                              # counts: K=20 cluster x group
    pct = ct.div(ct.sum(axis=1), axis=0) * 100                # % of each K=20 cluster
    main = pct.idxmax(axis=1); purity = pct.max(axis=1)
    summary[ng] = pd.DataFrame({"% of particles": share20.round(2), f"main group ({ng})": main,
                                f"% in it ({ng})": purity.round(1)})
    if j == 0:
        fig, ax = plt.subplots(figsize=(1.0 * ng + 4, 9))
        im = ax.imshow(pct.reindex(columns=range(ng), fill_value=0).to_numpy(), cmap="Blues", vmin=0, vmax=100,
                       aspect="auto")
        for r in range(K20):
            for c in range(ng):
                v_ = pct.reindex(columns=range(ng), fill_value=0).iat[r, c]
                if v_ >= 1:
                    ax.text(c, r, f"{v_:.0f}", ha="center", va="center", fontsize=7,
                            color="white" if v_ > 60 else "k")
        ax.set_xticks(range(ng)); ax.set_yticks(range(K20))
        ax.set_yticklabels([f"{r} ({share20[r]:.2g}%)" for r in range(K20)], fontsize=8)
        ax.set_xlabel(f"hierarchical group ({ng}-group cut of the K={K} fit)")
        ax.set_ylabel("K=20 cluster (share of all particles)")
        ax.set_title(f"Where the particles of each K=20 cluster end up among the {ng} hierarchical groups (% of the cluster)")
        fig.colorbar(im, ax=ax, label="% of the K=20 cluster", shrink=.7)
        fig.tight_layout(); plt.show()

tab20 = pd.concat([summary[CROSS_CUTS[0]]] + [summary[ng].iloc[:, 1:] for ng in CROSS_CUTS[1:]], axis=1)
tab20.index.name = "K=20 cluster"
for ng in CROSS_CUTS:
    pur = summary[ng][f"% in it ({ng})"]
    w = summary[ng]["% of particles"]
    print(f"{ng} groups: {int((pur >= 80).sum())} of {K20} K=20 clusters are >= 80% in one group; "
          f"particle-weighted agreement {np.average(pur, weights=w):.1f}%")
tab20.sort_values("% of particles", ascending=False)
"""),
])

# =========================================================================== #
# Explainer: direction-balanced sampling (used in v2.1.5 / v3.1.5)
# =========================================================================== #
# =========================================================================== #
# v4.1.5 - v3 + a 750 km radius (200, 500, 750, 1000, 1500, 2000 km)
# =========================================================================== #
save("v4.1.5_Manual_clustering.ipynb", [
md(r"""
# v4.1.5 - Manual clustering: v3 + a 750 km radius

Same method as **v3.1.5** (fit on `complete` + `partial`, direction-balanced
sample with alpha = 0, K sweep with 3 seeds, pathways >= 400 km apart that
reappear in every run, NBC-box exit sides, hierarchical view, real tracks),
with one change: the circles are **200, 500, 750, 1000, 1500, 2000 km**.

**Why 750 km.** Between 500 and 1000 km there was no circle, so where a route
turns in that stretch (e.g. the retroflection around 6-8N) only showed up as a
straight segment from the 500 km to the 1000 km point; some clusters did not
cover that gap. A 750 km circle puts a point there.

**Weights.** The same radius² ramp as v3, now over six radii (mean 1):
`{200: 0.030, 500: 0.185, 750: 0.417, 1000: 0.741, 1500: 1.667, 2000: 2.964}`.
Adding a radius also adds its weight, so the 1000-2000 km points count a
little less than in v3 relative to the whole.

**Data.** The 750 km exit points are in `data/features_r750.parquet`
(extracted by `data/extract_r750.py`, same row order as `features.parquet`,
same rule: a particle that never gets 750 km away keeps its last position).
`features.parquet` itself is unchanged, so v3 still works as before.

**Comparison with v3.** The K sweep below is run for v4; v3's saved sweep
(5 radii, same samples and seeds) is drawn next to it. Pathway distances now
average over six points instead of five, so counts are close but not exactly
like-for-like. (In the radius experiments on 3 M particles, a set with 50-2000
km including 750 km had slightly fewer separated pathways than the 5 radii -
18.5 vs 19.2 - but that test did not target the 500-1000 km gap.)

The 1.5 cross-check of v3 (K = 20 fit) is not repeated here.
"""),
code(BOOT + r"""
import time
import matplotlib.pyplot as plt
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
"""),
params_code(r"""
K_SWEEP = [50, 100, 150, 200, 250, 300, 400, 500]   # K values to try
RADII_V4 = [200, 500, 750, 1000, 1500, 2000]          # v3 radii + 750 km
# radius weights ~ radius^2 (as v3), over the six radii, mean 1
RADIUS_WEIGHTS = {200: 0.030, 500: 0.185, 750: 0.417, 1000: 0.741, 1500: 1.667, 2000: 2.964}
RUN_COMPARISON = True            # draw v3's saved sweep (5 radii) next to v4's
RUN_SWEEP = False                # False: load the saved v4 sweep (data/experiments/v4_k_sweep.csv) once it exists; True: recompute (~12 min)
# box used to classify how pathways leave the NBC region (lon0, lon1, lat0, lat1)
# = (west, east, south, north). The NBC box is 55-45W / 5-10N; its west side is
# moved out to 56.2W and its north side to 11N; east (45W) and south (5N) are the
# original NBC box.
NBC_BOX = (-56.2, -45.0, 5.0, 11.0)
SEEDS = [42, 1, 7]               # repeated fits (different sample + seed) for reproducibility
BALANCE_ALPHA = 0.0              # 1 as they come, 0 every direction sector equally
PATHWAY_SEP_KM = 400             # two pathways differ if their tracks are >= this far apart (mean over radii)
MATCH_KM = 200                   # a pathway is reproduced if another run has one within this distance
N_SUB = 500_000                  # particles per fit
K = None                         # final K; None -> chosen automatically from the sweep
SAVE_MODEL = False               # True -> write the final fit for notebooks 03 / 04
"""),
code(r"""
FIT_STATUS = ["complete", "partial"]
SECTOR_DEG = 15
C.RADII_KM = RADII_V4            # v4: every pipeline helper (feature columns, weights) now uses the six radii
W = P.feature_weight_vector(RADIUS_WEIGHTS)
print("radii:", C.RADII_KM, "| weights:", RADIUS_WEIGHTS,
      "| balance alpha:", BALANCE_ALPHA,
      "| separation:", PATHWAY_SEP_KM, "km")
"""),
md(r"""
## Particles to fit, and their outer direction
"""),
code(r"""
features = pd.read_parquet(C.FEATURES_FILE)
_r750 = pd.read_parquet(C.DATA_DIR / "features_r750.parquet")   # 750 km exit points, same row order
assert len(_r750) == len(features), "features_r750.parquet does not match features.parquet - re-run data/extract_r750.py"
for _c in _r750.columns:
    features[_c] = _r750[_c].to_numpy()
del _r750
fitset = features[features.status.isin(FIT_STATUS)].reset_index(drop=True)
del features
R_OUT = C.RADII_KM[-1]
bearing = P.bearing_deg(fitset.cross_lat, fitset.cross_lon,
                        fitset[P.lat_col(R_OUT)], fitset[P.lon_col(R_OUT)])
sector = np.clip(np.floor((bearing + 180) / SECTOR_DEG).astype(int), 0, 360 // SECTOR_DEG - 1)
n_sector = np.bincount(sector, minlength=360 // SECTOR_DEG)
X_all = P.build_feature_matrix(fitset)

tab = pd.DataFrame({"particles": n_sector,
                    "%": (100 * n_sector / n_sector.sum()).round(3)},
                   index=pd.Index([f"{-180 + SECTOR_DEG*i:+4d}..{-180 + SECTOR_DEG*(i+1):+4d}"
                                   for i in range(len(n_sector))], name="direction (deg, 0 N, -90 W)"))
print(f"{len(fitset):,} particles ({', '.join(FIT_STATUS)})")
print(tab[tab.particles > 0].to_string())

def balanced_sample(seed):
    rng = np.random.default_rng(seed)
    w = n_sector[sector].astype(float) ** (BALANCE_ALPHA - 1.0)
    return rng.choice(len(fitset), size=min(N_SUB, len(fitset)), replace=False, p=w / w.sum())

idx0 = balanced_sample(SEEDS[0])
print(f"\nshare with an eastward outer direction: all {100*(bearing > 0).mean():.1f}%, "
      f"in a balanced sample {100*(bearing[idx0] > 0).mean():.1f}%")
"""),
md(r"""
## Helpers: fit, centroids in degrees, distinct pathways
Centroids in degrees are the mean member position per radius. Track distance =
mean haversine distance between two centroids' exit points over the radii.
"""),
code(r"""
def track_dist(A, B):
    nr = A.shape[1] // 2
    D = 0
    for j in range(nr):
        D = D + P.haversine_km(A[:, None, 2*j], A[:, None, 2*j+1], B[None, :, 2*j], B[None, :, 2*j+1])
    return D / nr

def fit_k(k, idx, seed, n_init=10, Wv=None):
    Wv = W if Wv is None else Wv
    X = X_all[idx]
    sc = StandardScaler().fit(X)
    km = MiniBatchKMeans(n_clusters=k, random_state=seed, batch_size=10000,
                         n_init=n_init, max_iter=300).fit(sc.transform(X) * Wv)
    cent = pd.DataFrame(X).groupby(km.labels_).mean().reindex(range(k)).to_numpy()
    return km, sc, cent

def pathways(cent):
    # flat groups of centroids; every pair of groups is >= PATHWAY_SEP_KM apart
    Z = linkage(squareform(track_dist(cent, cent), checks=False), "complete")
    g = fcluster(Z, t=PATHWAY_SEP_KM, criterion="distance") - 1
    return g, np.array([cent[g == i].mean(axis=0) for i in range(g.max() + 1)])

def is_east(tracks, start_lon):
    return P.bearing_deg(C.LAT_CROSS, start_lon, tracks[:, -2], tracks[:, -1]) > 0

BOX = dict(lon0=NBC_BOX[0], lon1=NBC_BOX[1], lat0=NBC_BOX[2], lat1=NBC_BOX[3])   # grouping box
def _inside(lo, la):
    return BOX["lon0"] <= lo <= BOX["lon1"] and BOX["lat0"] <= la <= BOX["lat1"]

def exit_face(lons, lats):
    # side of the NBC box (N, W, E, S) through which a track first leaves it after
    # entering; 'none' = never inside, 'stays' = still inside at its last point
    was_in = False
    for k in range(len(lons) - 1):
        p, q = (lons[k], lats[k]), (lons[k + 1], lats[k + 1])
        if _inside(*p):
            was_in = True
            if not _inside(*q):
                dx, dy, ts = q[0] - p[0], q[1] - p[1], {}
                if dy > 0: ts["N"] = (BOX["lat1"] - p[1]) / dy
                if dy < 0: ts["S"] = (BOX["lat0"] - p[1]) / dy
                if dx < 0: ts["W"] = (BOX["lon0"] - p[0]) / dx
                if dx > 0: ts["E"] = (BOX["lon1"] - p[0]) / dx
                return min(ts, key=ts.get)
        elif not was_in:
            if _inside(*q):
                was_in = True
            else:                                   # segment may cross the whole box
                for t in np.linspace(0, 1, 50)[1:-1]:
                    x, y = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
                    if _inside(x, y):
                        sub_t = np.linspace(t, 1, 50)
                        return exit_face(list(p[0] + sub_t * (q[0] - p[0])),
                                         list(p[1] + sub_t * (q[1] - p[1])))
    return "stays" if was_in else "none"

def faces(tracks, starts):
    return [exit_face(list(np.r_[starts[i], tracks[i, 1::2]]), list(np.r_[C.LAT_CROSS, tracks[i, 0::2]]))
            for i in range(len(tracks))]

# one colour per exit side of the grouping box, used by every pathway map
FACE_COL = {"N": "tab:blue", "W": "tab:green", "E": "tab:red", "S": "tab:purple", "none": "0.5", "stays": "k"}
"""),
md(r"""
## Sweep K: number of distinct pathways and their reproducibility
For every K and seed: fit, group the centroids into pathways, count them (and
the eastward ones), and check whether each pathway reappears in the other runs.
"""),
code(r"""
start_all = fitset.cross_lon.to_numpy()

def run_sweep(Wv, label):
    rows, runs = [], {}
    for k in K_SWEEP:
        for seed in SEEDS:
            idx = balanced_sample(seed)
            km_s, sc_s, cent = fit_k(k, idx, seed, Wv=Wv)
            g, ptrack_s = pathways(cent)
            slon = pd.Series(start_all[idx]).groupby(km_s.labels_).mean().reindex(range(k)).to_numpy()
            pstart_s = np.array([slon[g == i].mean() for i in range(g.max() + 1)])
            fc = faces(ptrack_s, pstart_s)
            runs[(k, seed)] = ptrack_s
            rows.append(dict(weights=label, K=k, seed=seed, pathways=len(ptrack_s),
                             east=int(is_east(ptrack_s, pstart_s).sum()),
                             **{f"exit_{f}": fc.count(f) for f in ("N", "W", "E", "S")}))
        for seed in SEEDS:                   # reproducibility of each run's pathways
            others = [runs[(k, s)] for s in SEEDS if s != seed]
            ok = np.all([track_dist(runs[(k, seed)], o).min(axis=1) < MATCH_KM for o in others], axis=0)
            next(r for r in rows if r["K"] == k and r["seed"] == seed)["reproduced_%"] = round(100 * ok.mean())
        print(f"[{label}] K={k:4d}: " + ", ".join(
            f"{r['pathways']} ({r['east']} east, {r['reproduced_%']}%)" for r in rows if r["K"] == k), flush=True)
    return pd.DataFrame(rows)

SWEEP_CACHE = C.DATA_DIR / "experiments" / "v4_k_sweep.csv"
if RUN_SWEEP or not SWEEP_CACHE.exists():
    sweep = run_sweep(W, "v4")
    sweep.to_csv(SWEEP_CACHE, index=False)
else:
    sweep = pd.read_csv(SWEEP_CACHE)
    print("loaded saved sweep:", SWEEP_CACHE, "(set RUN_SWEEP = True to recompute)")
sweep_cmp = None
if RUN_COMPARISON:              # v3 = same method with 5 radii (its saved sweep, weights ~ r²)
    _v3 = pd.read_csv(C.DATA_DIR / "experiments" / "v3_k_sweep.csv")
    sweep_cmp = _v3[_v3.weights == "r2"].assign(weights="v3").reset_index(drop=True)
cols = [c for c in ["pathways", "east", "exit_N", "exit_W", "exit_E", "exit_S", "reproduced_%"] if c in sweep]
pd.concat([sweep, sweep_cmp]).groupby(["weights", "K"])[cols].mean().round(1)
"""),
code(r"""
def agg(sw):
    sw = sw.assign(rp=sw.pathways * sw["reproduced_%"] / 100)   # reproducible pathways per run
    return sw.groupby("K").agg(p=("pathways", "mean"), pmin=("pathways", "min"), pmax=("pathways", "max"),
                               e=("east", "mean"), r=("reproduced_%", "mean"),
                               rp=("rp", "mean"), rpmin=("rp", "min"), rpmax=("rp", "max"))
s = agg(sweep)
fig, ax = plt.subplots(1, 2, figsize=(13, 4))
ax[0].fill_between(s.index, s.pmin, s.pmax, color="0.85", lw=0, label="min-max over seeds (v4)")
ax[0].plot(s.index, s.p, "o-", color="k", label="all pathways, v4 (6 radii)")
ax[0].plot(s.index, s.e, "s-", color="tab:red", label="eastward, v4 (6 radii)")
ax[1].fill_between(s.index, s.rpmin, s.rpmax, color="lightblue", alpha=.5, lw=0, label="min-max over seeds (v4)")
ax[1].plot(s.index, s.rp, "o-", color="tab:blue", label="v4 (6 radii)")
if sweep_cmp is not None:
    sc_ = agg(sweep_cmp)
    ax[0].plot(sc_.index, sc_.p, "o--", color="0.5", label="all pathways, v3 (5 radii)")
    ax[0].plot(sc_.index, sc_.e, "s--", color="salmon", label="eastward, v3 (5 radii)")
    ax[1].plot(sc_.index, sc_.rp, "o--", color="slategray", label="v3 (5 radii)")
ax[0].set_xlabel("K"); ax[0].set_ylabel(f"pathways >= {PATHWAY_SEP_KM} km apart")
ax[0].legend(frameon=False, fontsize=8); ax[0].grid(color="0.92")
ax[1].legend(frameon=False, fontsize=8)
ax[1].set_xlabel("K"); ax[1].set_ylabel("reproducible pathways (found in every other run)")
ax[1].grid(color="0.92")
fig.suptitle(f"balance alpha {BALANCE_ALPHA}, fit on {', '.join(FIT_STATUS)}"); fig.tight_layout(); plt.show()

# choice: most pathways among the K whose pathways are >= 95% reproduced (smaller K on ties)
good = s[s.r >= 95]
K_AUTO = int((good if len(good) else s).sort_values(["p", "r"], ascending=[False, False]).index[0])
print(f"suggested K = {K_AUTO}: {s.loc[K_AUTO, 'p']:.1f} pathways "
      f"({s.loc[K_AUTO, 'e']:.1f} eastward), {s.loc[K_AUTO, 'r']:.0f}% reproduced "
      f"= {s.loc[K_AUTO, 'rp']:.1f} reproducible pathways")
_tab = s[["p", "rp", "r", "e"]].rename(columns={"p": "pathways", "rp": "reproducible", "r": "% reproduced", "e": "eastward"})
if sweep_cmp is not None:
    _tab = pd.concat({"v4 (6 radii)": _tab, "v3 (5 radii)": sc_[["p", "rp", "r", "e"]].rename(
        columns={"p": "pathways", "rp": "reproducible", "r": "% reproduced", "e": "eastward"})}, axis=1)
print(_tab.round(1).to_string())
if sweep_cmp is not None:
    ref = sc_.loc[400] if 400 in sc_.index else sc_.iloc[-1]
    match = s[(s.p >= ref.p) & (s.e >= ref.e)]
    print(f"v3 at K={int(ref.name)}: {ref.p:.1f} pathways ({ref.e:.1f} eastward); "
          f"v4 reaches that from K = {int(match.index.min()) if len(match) else 'none of the K tried'}")
if K is None:
    K = K_AUTO
print("K used below:", K)
"""),
md(r"""
## Final fit at K
Same balanced sample as the first seed, more initialisations. The pathway of
each cluster (`PATH_OF`) and the share of ALL particles in each pathway (from
labelling a random 2 million) are what the next steps of 1.5 build on.
"""),
code(r"""
idx = balanced_sample(SEEDS[0])
sub = fitset.iloc[idx].reset_index(drop=True)
km, scaler, cent_deg = fit_k(K, idx, SEEDS[0], n_init=20)
labels = km.labels_
sizes = np.bincount(labels, minlength=K)
start_lon = sub.groupby(labels).cross_lon.mean().reindex(range(K)).to_numpy()
def centroid_track(c):
    return (np.r_[start_lon[c], cent_deg[c, 1::2]],
            np.r_[C.LAT_CROSS, cent_deg[c, 0::2]])

PATH_OF, ptrack = pathways(cent_deg)
n_path = len(ptrack)
pstart = np.array([start_lon[PATH_OF == i].mean() for i in range(n_path)])
p_east = is_east(ptrack, pstart)
p_face = np.array(faces(ptrack, pstart))

ps = np.random.default_rng(0).choice(len(fitset), size=min(2_000_000, len(fitset)), replace=False)
lab_ps = km.predict(scaler.transform(X_all[ps]) * W)
share = 100 * np.bincount(PATH_OF[lab_ps], minlength=n_path) / len(ps)
cl_count = np.bincount(lab_ps, minlength=K)          # real particles per cluster (in the 2M sample)
ptab = pd.DataFrame({"clusters": np.bincount(PATH_OF, minlength=n_path),
                     "% of all particles": share.round(3), "eastward": p_east,
                     "leaves NBC box via": p_face,
                     f"exit lat {R_OUT}km": ptrack[:, -2].round(1),
                     f"exit lon {R_OUT}km": ptrack[:, -1].round(1)})
ptab.index.name = "pathway"
print(f"fit K={K} on {len(sub):,} particles (balanced) | {n_path} pathways, "
      f"{int(p_east.sum())} eastward | cluster sizes {sizes.min()}..{sizes.max()}")
print("pathways by NBC-box exit side:", pd.Series(p_face).value_counts().to_dict())
ptab.sort_values("% of all particles", ascending=False)
"""),
code(r"""
# Persist THIS fit for notebooks 03 / 04 (only when SAVE_MODEL is True).
import joblib, json
if SAVE_MODEL:
    MODEL_DIR = C.manual_model_dir(K)
    if MODEL_DIR.exists():
        print("NOTE: overwriting", MODEL_DIR)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(km, MODEL_DIR / f"kmeans_k{K}.pkl")
    joblib.dump(scaler, MODEL_DIR / "scaler.pkl")
    np.save(MODEL_DIR / "weights_W.npy", W)
    np.save(MODEL_DIR / "centroids_deg.npy", cent_deg)
    np.save(MODEL_DIR / "pathway_of_cluster.npy", PATH_OF)
    sub[["trajectory_id", "store", "row", "traj"]].assign(cluster=labels).to_parquet(
        MODEL_DIR / "subsample_labels.parquet", index=False)
    pd.concat([sweep, sweep_cmp]).to_csv(MODEL_DIR / "k_sweep.csv", index=False)
    (MODEL_DIR / "fit_metadata.json").write_text(json.dumps(dict(
        source_notebook="v4.1.5_Manual_clustering.ipynb", K=K, LAT_CROSS=C.LAT_CROSS,
        RADII_KM=C.RADII_KM, RADIUS_WEIGHTS={str(k): v for k, v in RADIUS_WEIGHTS.items()},
        FIT_STATUS=FIT_STATUS, BALANCE_ALPHA=BALANCE_ALPHA, SECTOR_DEG=SECTOR_DEG,
        PATHWAY_SEP_KM=PATHWAY_SEP_KM, n_pathways=int(n_path), N_SUB=N_SUB,
        seed=SEEDS[0], n_fitted=int(len(sub)), cluster_sizes=sizes.tolist()), indent=2))
    print("saved model ->", MODEL_DIR)
else:
    print("SAVE_MODEL is False -> nothing written")
"""),
md(r"""
## Cheap coastline
"""),
code(REFS + r"""
_draw_refs_base = draw_refs
def draw_refs(ax, **kw):
    # reference lines + the grouping box (dashed) on top of the NBC box (green)
    _draw_refs_base(ax, **kw)
    ax.add_patch(mpatches.Rectangle((BOX["lon0"], BOX["lat0"]), BOX["lon1"] - BOX["lon0"],
                                    BOX["lat1"] - BOX["lat0"], fill=False, ec="darkgreen",
                                    ls="--", lw=1.2, zorder=1))
import cartopy.feature as cfeature
lon_lim = (C.DOMAIN["lon_min"], C.DOMAIN["lon_max"])
lat_lim = (C.DOMAIN["lat_min"], C.DOMAIN["lat_max"])
_coast = []
for geom in cfeature.COASTLINE.with_scale("110m").geometries():
    for line in getattr(geom, "geoms", [geom]):
        _coast.append((np.asarray(line.xy[0]), np.asarray(line.xy[1])))
def draw_coast(ax):
    for x, y in _coast:
        ax.plot(x, y, "-", color="0.75", lw=.4, zorder=0)
    ax.set_xlim(*lon_lim); ax.set_ylim(*lat_lim)
"""),
md(r"""
## All clusters on one map
Top left: every centroid track, coloured by its pathway (one colour per pathway). The other three
panels draw one line per pathway in three ways (label = pathway number and its
share of all particles; line width ~ share). In these three panels every line is
coloured by the side of the grouping box (`NBC_BOX`, dashed) it leaves through: N blue, W green, E red,
S purple, stays inside black, never enters grey:

* **plain mean** of the pathway's centroids (every cluster counts the same);
* **size-weighted mean**: each centroid weighted by how many real particles
  it gets when a random 2 million particles are labelled, so big clusters
  count more (the fit sample was balanced, so cluster sizes in the fit do not
  show how common a route is);
* **representative cluster**: the real centroid of the pathway whose track is
  closest, on average, to all the others in it - a track that some cluster
  actually has, not an average of several.

Zigzags in the eastward lines come from particles whose track ends before
1500 / 2000 km: their "exit" there is the last position, which can lie inside
the circle.
"""),
code(r"""
def mean_tracks(weights):
    tr, st = [], []
    for i in range(n_path):
        m = PATH_OF == i
        w = weights[m] if weights[m].sum() > 0 else np.ones(m.sum())
        tr.append(np.average(cent_deg[m], axis=0, weights=w))
        st.append(np.average(start_lon[m], weights=w))
    return np.array(tr), np.array(st)

def representative_tracks():
    tr, st, rep = [], [], []
    for i in range(n_path):
        mem = np.where(PATH_OF == i)[0]
        D = track_dist(cent_deg[mem], cent_deg[mem])
        c = mem[D.mean(axis=1).argmin()]        # closest on average to the other members
        tr.append(cent_deg[c]); st.append(start_lon[c]); rep.append(c)
    return np.array(tr), np.array(st), np.array(rep)

tr_plain, st_plain = mean_tracks(np.ones(K))
tr_wmean, st_wmean = mean_tracks(cl_count.astype(float))
tr_rep, st_rep, REP_OF = representative_tracks()

pcmap = plt.get_cmap("tab20", max(n_path, 3))
la_all = np.r_[cent_deg[:, 0::2].ravel(), C.LAT_CROSS]; lo_all = cent_deg[:, 1::2].ravel()
zoom = (lo_all.min() - 3, lo_all.max() + 3, min(la_all.min(), 0) - 2, la_all.max() + 3)

def face_legend(ax, used):
    ax.legend(handles=[plt.Line2D([], [], color=c, lw=2, label=k) for k, c in FACE_COL.items() if k in used],
              title="leaves the box via", frameon=False, loc="lower right")

def draw_pathways(ax, tracks, starts, title):
    # each pathway coloured by the side of the grouping box its drawn track leaves through
    draw_coast(ax); draw_refs(ax)
    fc = faces(tracks, starts)
    for i in range(n_path):
        lo = np.r_[starts[i], tracks[i, 1::2]]; la = np.r_[C.LAT_CROSS, tracks[i, 0::2]]
        ax.plot(lo, la, ".-", color=FACE_COL[fc[i]],
                lw=1 + 3 * np.sqrt(share[i] / share.max()), zorder=3)
        ax.text(lo[-1], la[-1], f" {i} ({share[i]:.2g}%)", fontsize=7, zorder=4)
    face_legend(ax, set(fc))
    ax.set_title(title)

fig, axes = plt.subplots(2, 2, figsize=(18, 15), sharex=True, sharey=True)
ax = axes[0, 0]
draw_coast(ax); draw_refs(ax)
for c in range(K):
    lo, la = centroid_track(c)
    ax.plot(lo, la, "-", color=pcmap(PATH_OF[c]), lw=.8, alpha=.7, zorder=2)
ax.set_title(f"All {K} centroid tracks, coloured by pathway ({n_path} pathways "
             f">= {PATHWAY_SEP_KM} km apart)")
draw_pathways(axes[0, 1], tr_plain, st_plain, "Pathways: plain mean of their centroids")
draw_pathways(axes[1, 0], tr_wmean, st_wmean, "Pathways: mean weighted by real particles per cluster")
draw_pathways(axes[1, 1], tr_rep, st_rep, "Pathways: representative cluster (a real centroid)")
for a in axes.ravel():
    a.set_xlim(zoom[0], zoom[1]); a.set_ylim(zoom[2], zoom[3])
fig.tight_layout(); plt.show()

# how far apart the three versions are, per pathway (mean over radii, km)
diff = pd.DataFrame({
    "% of particles": share.round(3), "clusters": np.bincount(PATH_OF, minlength=n_path),
    "representative cluster": REP_OF,
    "plain vs weighted [km]": np.diag(track_dist(tr_plain, tr_wmean)).round(0),
    "plain vs representative [km]": np.diag(track_dist(tr_plain, tr_rep)).round(0),
    "weighted vs representative [km]": np.diag(track_dist(tr_wmean, tr_rep)).round(0)},
    index=pd.Index(range(n_path), name="pathway"))
diff.sort_values("% of particles", ascending=False)
"""),
md(r"""
## Pathways by how they leave the NBC box
Representative cluster of each pathway (the tracks drawn here are also the
ones classified). Green box = NBC box 55-45W / 5-10N.

* **Left:** coloured by the first side the pathway leaves the box through.
* **Right:** pathways that leave the box **two or more times** - they exit,
  come back in, and exit again - coloured by the order of the sides, e.g.
  `N → E` = out through the north side, back in, out through the east side.
  Pathways that leave only once are grey.

The track is followed in small steps along each straight piece between the
points at 2.5N, 200, 500, 1000, 1500 and 2000 km, so a crossing between two
points is not missed.
"""),
code(r"""
def box_sequence(lons, lats, n_sub=200):
    # every exit from (and entry into) the NBC box along the track, in order
    lo = np.concatenate([np.linspace(lons[k], lons[k + 1], n_sub, endpoint=False) for k in range(len(lons) - 1)] + [[lons[-1]]])
    la = np.concatenate([np.linspace(lats[k], lats[k + 1], n_sub, endpoint=False) for k in range(len(lats) - 1)] + [[lats[-1]]])
    ins = (lo >= BOX["lon0"]) & (lo <= BOX["lon1"]) & (la >= BOX["lat0"]) & (la <= BOX["lat1"])
    def side(x, y):              # side of the box a point just outside it lies beyond
        d = {"N": y - BOX["lat1"], "S": BOX["lat0"] - y, "W": BOX["lon0"] - x, "E": x - BOX["lon1"]}
        return max(d, key=d.get)
    exits, entries = [], []
    for k in range(len(ins) - 1):
        if ins[k] and not ins[k + 1]:
            exits.append(side(lo[k + 1], la[k + 1]))
        elif not ins[k] and ins[k + 1]:
            entries.append(side(lo[k], la[k]))
    return exits, entries, bool(ins[-1])

def seq_label(exits, ends_inside):
    if not exits:
        return "stays" if ends_inside else "none"
    lab = " → ".join(exits)
    return lab + " (ends inside)" if ends_inside else lab

seq = [box_sequence(np.r_[st_rep[i], tr_rep[i, 1::2]], np.r_[C.LAT_CROSS, tr_rep[i, 0::2]]) for i in range(n_path)]
first_exit = np.array([ex[0] if ex else ("stays" if end else "none") for ex, _, end in seq])
n_exits = np.array([len(ex) for ex, _, _ in seq])
seq_lab = np.array([seq_label(ex, end) for ex, _, end in seq])

bt = pd.DataFrame({"% of particles": share.round(3), "first exit": first_exit, "times it leaves": n_exits,
                   "exit sequence": seq_lab, "enters through": [" → ".join(en) for _, en, _ in seq]},
                  index=pd.Index(range(n_path), name="pathway"))
print("first exit side:", pd.Series(first_exit).value_counts().to_dict())
print("leave the box 2+ times:", int((n_exits >= 2).sum()), "pathways,",
      f"{share[n_exits >= 2].sum():.3f}% of particles;",
      pd.Series(seq_lab[n_exits >= 2]).value_counts().to_dict())

multi = sorted(set(seq_lab[n_exits >= 2]))
mcmap = plt.get_cmap("tab10", max(len(multi), 3))
SEQ_COL = {L: mcmap(i) for i, L in enumerate(multi)}

fig, axes = plt.subplots(1, 2, figsize=(22, 8.5), sharex=True, sharey=True)
for ax in axes:
    draw_coast(ax); draw_refs(ax)
    ax.set_xlim(zoom[0], zoom[1]); ax.set_ylim(zoom[2], zoom[3])
for i in range(n_path):
    lo = np.r_[st_rep[i], tr_rep[i, 1::2]]; la = np.r_[C.LAT_CROSS, tr_rep[i, 0::2]]
    lw = 1 + 3 * np.sqrt(share[i] / share.max())
    axes[0].plot(lo, la, ".-", color=FACE_COL[first_exit[i]], lw=lw, zorder=3)
    axes[0].text(lo[-1], la[-1], f" {i} ({share[i]:.2g}%)", fontsize=7, zorder=4)
    if n_exits[i] >= 2:
        axes[1].plot(lo, la, ".-", color=SEQ_COL[seq_lab[i]], lw=max(lw, 2), zorder=4)
        axes[1].text(lo[-1], la[-1], f" {i} ({share[i]:.2g}%)", fontsize=7, zorder=5)
    else:
        axes[1].plot(lo, la, "-", color="0.8", lw=.8, zorder=2)
axes[0].legend(handles=[plt.Line2D([], [], color=c, lw=2, label=k) for k, c in FACE_COL.items()
                        if k in set(first_exit)], title="first exit side", frameon=False, loc="lower right")
axes[0].set_title(f"K={K}: {n_path} pathways by first exit side: " + ", ".join(
    f"{k} {v}" for k, v in pd.Series(first_exit).value_counts().items()))
axes[1].legend(handles=[plt.Line2D([], [], color=c, lw=2, label=k) for k, c in SEQ_COL.items()]
               + [plt.Line2D([], [], color="0.8", lw=1, label="leaves once")],
               title="exit sequence (out, back in, out ...)", frameon=False, loc="lower right")
axes[1].set_title(f"Pathways that leave the box 2+ times: {int((n_exits >= 2).sum())} "
                  f"({share[n_exits >= 2].sum():.2g}% of particles)")
fig.tight_layout(); plt.show()
bt.sort_values(["times it leaves", "% of particles"], ascending=False)
"""),
md(r"""
## Hierarchical view: how the clusters group into pathways
The pathways above are made by **complete-linkage** clustering of the centroid
tracks (distance = mean distance between their points at 200 ... 2000 km),
cut at `PATHWAY_SEP_KM`. The dendrograms show that tree:

* **left:** all K centroids (only the top of the tree, the last merges, is
  drawn); dashed line = the cut, every branch below it is one pathway;
* **right:** the pathways themselves (representative tracks), labelled with
  pathway number, first exit side of the grouping box and share of particles -
  pathways that join low in this tree are the closest candidates to merge by
  hand.
"""),
code(r"""
from scipy.cluster.hierarchy import dendrogram
Z_cl = linkage(squareform(track_dist(cent_deg, cent_deg), checks=False), "complete")
Z_pw = linkage(squareform(track_dist(tr_rep, tr_rep), checks=False), "complete")
fig, ax = plt.subplots(1, 2, figsize=(20, 6.5), gridspec_kw={"width_ratios": [1.1, 1]})
dendrogram(Z_cl, ax=ax[0], truncate_mode="lastp", p=min(3 * n_path, K), color_threshold=PATHWAY_SEP_KM,
           show_leaf_counts=True, leaf_rotation=90, leaf_font_size=7)
ax[0].axhline(PATHWAY_SEP_KM, color="k", ls="--", lw=.8)
ax[0].set_ylabel("complete-linkage distance (km)")
ax[0].set_title(f"{K} centroids -> {n_path} pathways (cut at {PATHWAY_SEP_KM} km); leaves = groups of clusters (count)")
labels = [f"{i} {first_exit[i]} {share[i]:.2g}%" for i in range(n_path)]
dn = dendrogram(Z_pw, ax=ax[1], labels=labels, leaf_rotation=90, leaf_font_size=8,
                color_threshold=0, above_threshold_color="0.4")
for t in ax[1].get_xticklabels():
    t.set_color(FACE_COL[t.get_text().split()[1]])
ax[1].set_ylabel("complete-linkage distance (km)")
ax[1].set_title("pathways (representative tracks): number, first exit side, % of particles")
fig.tight_layout(); plt.show()
"""),
md(r"""
## Hierarchical grouping of the clusters, on the map
The K centroid tracks are grouped by **complete-linkage** hierarchical
clustering (distance = mean distance between their points at 200 ... 2000 km,
the same distance as for the pathways) and the tree is cut into `N_GROUPS`
groups. Thin lines = centroid tracks coloured by group; thick line = the
group's mean track weighted by its real particles, labelled with group number
and share of all particles. Each panel is one cut, so going from left to
right shows which clusters split off first.
"""),
code(r"""
N_GROUPS = [4, 8, 12]           # cuts of the tree to show (one panel each)
import matplotlib.patheffects as pe
# Z_cl = the centroid tree of the left dendrogram above
fig, axes = plt.subplots(1, len(N_GROUPS), figsize=(9 * len(N_GROUPS), 8), sharex=True, sharey=True,
                         squeeze=False)
HGROUP = {}
for ax, ng in zip(axes[0], N_GROUPS):
    hg = fcluster(Z_cl, t=ng, criterion="maxclust") - 1
    HGROUP[ng] = hg
    gcmap = plt.get_cmap("tab10" if hg.max() < 10 else "tab20", max(hg.max() + 1, 3))
    draw_coast(ax); draw_refs(ax)
    for c in range(K):
        lo, la = centroid_track(c)
        ax.plot(lo, la, "-", color=gcmap(hg[c]), lw=.6, alpha=.45, zorder=2)
    for gi in range(hg.max() + 1):
        mem = hg == gi
        wts = cl_count[mem] if cl_count[mem].sum() > 0 else np.ones(mem.sum())
        tr = np.average(cent_deg[mem], axis=0, weights=wts)
        st = np.average(start_lon[mem], weights=wts)
        lo = np.r_[st, tr[1::2]]; la = np.r_[C.LAT_CROSS, tr[0::2]]
        g_share = 100 * cl_count[mem].sum() / cl_count.sum()
        ax.plot(lo, la, ".-", color=gcmap(gi), lw=4, zorder=4,
                path_effects=[pe.withStroke(linewidth=6, foreground="k")])
        ax.text(lo[-1], la[-1], f" {gi} ({g_share:.2g}%, {mem.sum()} cl)", fontsize=8, zorder=5,
                fontweight="bold", color=gcmap(gi))
    ax.set_xlim(zoom[0], zoom[1]); ax.set_ylim(zoom[2], zoom[3])
    ax.set_title(f"{K} clusters cut into {hg.max() + 1} hierarchical groups")
fig.tight_layout(); plt.show()

# which pathways (>= PATHWAY_SEP_KM apart) end up in which group, per cut
pd.DataFrame({f"group ({ng} groups)": [sorted(set(HGROUP[ng][PATH_OF == i])) for i in range(n_path)]
              for ng in N_GROUPS} | {"% of particles": share.round(3), "first exit": first_exit},
             index=pd.Index(range(n_path), name="pathway")).sort_values("% of particles", ascending=False)
"""),
md(r"""
## Hierarchical groups versus real trajectories
For the 8- and 12-group cuts above: one panel per group with real particle
tracks after the 2.5N crossing.

* **blue** = particles of the **fit sample** (the balanced 500,000 k-means was
  trained on) that fall in the group;
* **green** = particles **not** in the fit sample - k-means never saw them,
  they are only assigned to their nearest centroid. If a group is real, the
  green tracks follow the blue ones;
* **orange** = the group's mean track (weighted by real particles).

Title: group number, its share of all particles, and how many fit / non-fit
particles it has.
"""),
code(r"""
REAL_CUTS = [8, 12]              # which cuts of the tree to show (any number of groups)
MEMBERS_PER_GROUP = 25           # tracks of each kind (blue / green) per panel
N_IO_THREADS = int(os.environ.get("SLURM_CPUS_PER_TASK", 16))
for ng in REAL_CUTS:             # cuts not drawn on the map above are cut from the same tree here
    if ng not in HGROUP:
        HGROUP[ng] = fcluster(Z_cl, t=ng, criterion="maxclust") - 1

trained = np.zeros(len(fitset), dtype=bool); trained[idx] = True
nf = np.where(~trained)[0]                                   # rows of fitset not in the fit sample
lab_fit = km.labels_                                         # cluster of each fit-sample particle (order of idx)
lab_nf = km.predict(scaler.transform(X_all[nf]) * W)         # cluster of each non-fit particle
cols = ["trajectory_id", "store", "row", "traj", "cross_obs"]
picks = []
for ng in REAL_CUTS:
    hg = HGROUP[ng]
    for kind, rows_, labs in (("fit", idx, lab_fit), ("nonfit", nf, lab_nf)):
        d = fitset.iloc[rows_][cols].assign(group=hg[labs], kind=kind, cut=ng)
        picks.append(pd.concat([g.sample(min(MEMBERS_PER_GROUP, len(g)), random_state=C.RANDOM_STATE)
                                for _, g in d.groupby("group")]))
pick_all = pd.concat(picks, ignore_index=True)
gpaths = P.read_paths(pick_all.drop_duplicates("trajectory_id"), n_jobs=N_IO_THREADS)
print(f"read {len(gpaths):,} real tracks; {len(nf):,} non-fit particles labelled")

for ng in REAL_CUTS:
    hg = HGROUP[ng]
    n_fit = np.bincount(hg[lab_fit], minlength=hg.max() + 1)
    n_nf = np.bincount(hg[lab_nf], minlength=hg.max() + 1)
    ncol = 4; nrow = int(np.ceil((hg.max() + 1) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.6 * ncol, 3.6 * nrow), squeeze=False, sharex=True, sharey=True)
    for gi in range(hg.max() + 1):
        ax = axes[gi // ncol][gi % ncol]
        draw_coast(ax); draw_refs(ax)
        sel = pick_all[(pick_all.cut == ng) & (pick_all.group == gi)]
        for kind, col in (("nonfit", "green"), ("fit", "blue")):
            for tid, k0 in sel.loc[sel.kind == kind, ["trajectory_id", "cross_obs"]].itertuples(index=False):
                lo, la = gpaths[int(tid)]
                m = ~(np.isnan(lo[k0:]) | np.isnan(la[k0:]))
                ax.plot(lo[k0:][m], la[k0:][m], "-", color=col, lw=.5, alpha=.35, zorder=2)
        mem = hg == gi
        wts = cl_count[mem] if cl_count[mem].sum() > 0 else np.ones(mem.sum())
        tr = np.average(cent_deg[mem], axis=0, weights=wts); st = np.average(start_lon[mem], weights=wts)
        ax.plot(np.r_[st, tr[1::2]], np.r_[C.LAT_CROSS, tr[0::2]], ".-", color="darkorange", lw=2.5, zorder=4)
        ax.set_xlim(zoom[0], zoom[1]); ax.set_ylim(zoom[2], zoom[3])
        g_share = 100 * cl_count[mem].sum() / cl_count.sum()
        ax.set_title(f"group {gi}: {g_share:.2g}% of particles\nfit {n_fit[gi]:,} | non-fit {n_nf[gi]:,}", fontsize=9)
    for j in range(hg.max() + 1, nrow * ncol):
        axes[j // ncol][j % ncol].axis("off")
    fig.suptitle(f"{ng} hierarchical groups: blue = fit sample, green = not in the fit sample, "
                 f"orange = group mean track", y=1.0)
    fig.tight_layout(); plt.show()
"""),
])

# =========================================================================== #
# Explainer: direction-balanced sampling (used in v2.1.5 / v3.1.5)
# =========================================================================== #
save("explain_direction_balanced_sampling.ipynb", [
md(r"""
# What is the "direction-balanced sample"? (explainer for v2.1.5 / v3.1.5)

k-means is fitted on a **sample** of 500,000 of the ~15 million particles. This
notebook shows, step by step and with plots, how v2.1.5 / v3.1.5 choose that
sample, why, and what it changes.

**In one sentence:** every particle gets a *direction* (from where it crosses
2.5N to where it is at 2000 km, or where its track ends); the compass is cut
into 24 slices of 15°; and the 500,000 particles are drawn so that **every
slice contributes about the same number**, instead of in proportion to how
crowded it is. Only the fit sample is balanced - afterwards all particles are
labelled, so every share (%) that is reported is still the real one.

**Contents**
1. Why plain random sampling misses rare routes
2. One particle: its direction and its 15° sector
3. All 24 sectors on the map
4. How many particles per sector - before and after balancing
5. What k-means does with each sample
6. Why the reported shares are still the real ones
7. Background and references
"""),
code(BOOT + r"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import cartopy.feature as cfeature
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler

SECTOR_DEG = 15                  # width of one direction slice
N_SUB = 500_000                  # particles in the fit sample
SEED = 42
R_OUT = C.RADII_KM[-1]           # outermost radius (2000 km)
RADIUS_WEIGHTS = {200: 0.027, 500: 0.166, 1000: 0.663, 1500: 1.492, 2000: 2.653}   # as in v3
K_DEMO = 400

_coast = []
for geom in cfeature.COASTLINE.with_scale("110m").geometries():
    for line in getattr(geom, "geoms", [geom]):
        _coast.append((np.asarray(line.xy[0]), np.asarray(line.xy[1])))
def draw_coast(ax, lon=(-72, -25), lat=(-3, 22)):
    for x, y in _coast:
        ax.plot(x, y, "-", color="0.7", lw=.5, zorder=0)
    ax.set_xlim(*lon); ax.set_ylim(*lat); ax.set_aspect("equal")
    ax.axhline(C.LAT_CROSS, color="k", ls="--", lw=.6)

def compass(b):                  # bearing (deg, 0 = N, 90 = E, -90 = W) -> text
    names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return names[int(np.round((b % 360) / 22.5)) % 16]
"""),
md(r"""
## 1. Why plain random sampling misses rare routes

k-means puts its cluster centres **where the particles are dense**. With many
clusters, the density of centres follows the density of the data (raised to a
power a bit below 1; quantization theory, Gersho 1979). So if 86% of the
particles go one way and 3% another, the 3% get only a handful of centres -
however different their route is. Balancing the *sample* gives the rare routes
enough particles to get their own clusters.
"""),
md(r"""
## 2. One particle: its direction and its 15° sector

The **direction** of a particle = the compass direction from its crossing
point on 2.5N to its *outer point*: where it first gets 2000 km away, or - for
a `partial` particle whose track ends earlier - its last position. (0° = north,
90° = east, -90° = west.) The compass is cut into 24 slices of 15°; each
particle belongs to exactly one slice.
"""),
code(r"""
f = pd.read_parquet(C.FEATURES_FILE, columns=["status", "cross_lat", "cross_lon", "trajectory_id"]
                    + P.feature_columns())
fit = f[f.status.isin(["complete", "partial"])].reset_index(drop=True); del f
bearing = P.bearing_deg(fit.cross_lat, fit.cross_lon, fit[P.lat_col(R_OUT)], fit[P.lon_col(R_OUT)])
n_sec = 360 // SECTOR_DEG
sector = np.clip(np.floor((bearing + 180) / SECTOR_DEG).astype(int), 0, n_sec - 1)
edges = -180 + SECTOR_DEG * np.arange(n_sec + 1)                  # sector k covers edges[k] .. edges[k+1]
print(f"{len(fit):,} particles (complete + partial)")

# two example particles: one going north-west (common), one going east (rare)
ex = [int(np.where((bearing > -50) & (bearing < -40))[0][0]), int(np.where((bearing > 70) & (bearing < 80))[0][0])]
fig, axes = plt.subplots(1, 2, figsize=(17, 7))
for ax, i in zip(axes, ex):
    draw_coast(ax)
    la0, lo0 = fit.cross_lat[i], fit.cross_lon[i]
    la1, lo1 = fit[P.lat_col(R_OUT)][i], fit[P.lon_col(R_OUT)][i]
    # the 24 slices as thin lines from the crossing point, the particle's slice shaded
    for e in edges[:-1]:
        cla, clo = P.circle_latlon(la0, lo0, 2600, n=361)
        k = int(round((e % 360)))
        ax.plot([lo0, clo[k]], [la0, cla[k]], "-", color="0.85", lw=.6, zorder=1)
    k0 = sector[i]
    angs = np.arange(int(edges[k0]), int(edges[k0 + 1]) + 1) % 360
    cla, clo = P.circle_latlon(la0, lo0, 2600, n=361)
    ax.fill(np.r_[lo0, clo[angs], lo0], np.r_[la0, cla[angs], la0], color="gold", alpha=.35, zorder=1,
            label=f"its sector: {edges[k0]:.0f}° to {edges[k0+1]:.0f}°")
    ax.annotate("", xy=(lo1, la1), xytext=(lo0, la0),
                arrowprops=dict(arrowstyle="-|>", lw=2.5, color="tab:red"), zorder=3)
    ax.plot(lo0, la0, "ko", ms=7, zorder=4, label="crossing point on 2.5N")
    ax.plot(lo1, la1, "o", color="tab:red", ms=8, zorder=4,
            label=f"outer point ({'2000 km exit' if fit.status[i] == 'complete' else 'last position'})")
    ax.set_title(f"direction = {bearing[i]:.0f}° ({compass(bearing[i])}) -> sector {k0} "
                 f"({edges[k0]:.0f}°..{edges[k0+1]:.0f}°)")
    ax.legend(loc="lower left", fontsize=9)
fig.suptitle("Step 1: one direction and one 15° slice per particle (grey lines = all slice borders)", y=1.0)
fig.tight_layout(); plt.show()
"""),
md(r"""
## 3. All 24 sectors on the map

The slices drawn from the mean crossing point, with the outer points of 30,000
random particles coloured by their slice. Most points fall in a few slices to
the north-west; the eastern slices hold very few particles.
"""),
code(r"""
rng = np.random.default_rng(0)
show = rng.choice(len(fit), 30_000, replace=False)
la0, lo0 = fit.cross_lat.mean(), fit.cross_lon.mean()
cmap = plt.get_cmap("twilight", n_sec)
fig, ax = plt.subplots(figsize=(13, 8))
draw_coast(ax)
cla, clo = P.circle_latlon(la0, lo0, 2600, n=361)
for k in range(n_sec):
    angs = np.arange(int(edges[k]), int(edges[k + 1]) + 1) % 360
    ax.fill(np.r_[lo0, clo[angs], lo0], np.r_[la0, cla[angs], la0], color=cmap(k), alpha=.12, zorder=1)
    mid = int(round((edges[k] + SECTOR_DEG / 2) % 360))
    ax.text(clo[mid], cla[mid], f"{edges[k]:.0f}°", fontsize=7, ha="center", va="center", color="0.3")
ax.scatter(fit[P.lon_col(R_OUT)].to_numpy()[show], fit[P.lat_col(R_OUT)].to_numpy()[show],
           c=[cmap(k) for k in sector[show]], s=2, zorder=2)
ax.plot(lo0, la0, "ko", ms=6, zorder=3)
ax.set_title("24 slices of 15° around the (mean) crossing point; dots = outer points of 30,000 random particles\n"
             "(each particle's slice is measured from its OWN crossing point)")
fig.tight_layout(); plt.show()
"""),
md(r"""
## 4. How many particles per sector - before and after balancing

**Sampling weight.** Each particle gets a chance to be drawn proportional to
`n_sector ** (alpha - 1)`, where `n_sector` = how many particles share its
slice:

* `alpha = 1`: every particle the same chance -> the sample has the same mix as
  the data (as in 1.5);
* `alpha = 0`: chance ∝ 1 / n_sector -> every non-empty slice contributes about
  equally (as in v2 / v3);
* `alpha = 0.5`: in between - chance ∝ 1 / sqrt(n_sector); rare slices are
  boosted, but crowded slices still give more than rare ones.

v2.1.5 / v3.1.5 use **alpha = 0**; alpha = 0.5 is the gentler option.

Slices with very few particles cannot give more than they have; they are drawn
almost completely, so the "equal" share is approximate.
"""),
code(r"""
n_sector = np.bincount(sector, minlength=n_sec)
def balanced_sample(alpha, seed=SEED, n=N_SUB):
    w = n_sector[sector].astype(float) ** (alpha - 1.0)
    return np.random.default_rng(seed).choice(len(fit), size=min(n, len(fit)), replace=False, p=w / w.sum())

samples = {a: balanced_sample(a) for a in (1.0, 0.5, 0.0)}
tab = pd.DataFrame({"slice": [f"{edges[k]:+.0f}..{edges[k+1]:+.0f}° ({compass(edges[k] + 7.5)})" for k in range(n_sec)],
                    "particles": n_sector,
                    "% of all particles": 100 * n_sector / n_sector.sum()})
for a, idx in samples.items():
    tab[f"% of fit sample, alpha={a:g}"] = 100 * np.bincount(sector[idx], minlength=n_sec) / len(idx)
tab = tab[tab.particles > 0].set_index("slice")
print(tab.round(2).to_string())

centers = np.deg2rad(edges[:-1] + SECTOR_DEG / 2)
fig, axes = plt.subplots(1, 4, figsize=(24, 6), subplot_kw={"projection": "polar"})
for ax, (a, title) in zip(axes, [(None, "all particles"), (1.0, "fit sample, alpha = 1 (as in 1.5)"),
                                 (0.5, "fit sample, alpha = 0.5 (in between)"),
                                 (0.0, "fit sample, alpha = 0 (v2 / v3)")]):
    pct = tab["% of all particles"] if a is None else tab[f"% of fit sample, alpha={a:g}"]
    full = np.zeros(n_sec); full[n_sector > 0] = pct.to_numpy()
    ax.bar(centers, np.log10(1 + 100 * full), width=np.deg2rad(SECTOR_DEG) * .9,
           color=[cmap(k) for k in range(n_sec)], edgecolor="k", lw=.4)
    ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)       # compass: N up, clockwise
    ax.set_yticklabels([])
    ax.set_title(title, pad=18)
fig.suptitle("Share of particles per 15° slice (bar length ~ log of the share, so small slices stay visible)", y=1.02)
fig.tight_layout(); plt.show()

east = bearing > 0
for a, idx in samples.items():
    print(f"alpha={a:g}: share of the fit sample with an eastward direction = {100 * east[idx].mean():5.1f}%  "
          f"(all particles: {100 * east.mean():.1f}%)")
"""),
md(r"""
### The sampling rule as a formula

**Notation.** $N$ = sample size (500,000); $s(i)$ = direction slice of particle
$i$; $n_s$ = number of particles in slice $s$; $\alpha$ = `BALANCE_ALPHA`.

**1. Weight of each particle**

$$w_i = n_{s(i)}^{\,\alpha - 1}$$

* $\alpha = 1$: $w_i = 1$ - every particle equal (plain random sample);
* $\alpha = 0$: $w_i = 1/n_{s(i)}$ - the weights of one slice add up to
  $n_s \cdot 1/n_s = 1$, so **every slice has the same total weight**, whatever
  its size;
* $\alpha = 0.5$: $w_i = 1/\sqrt{n_{s(i)}}$ - slice total $= \sqrt{n_s}$.

**2. Drawing without replacement, one particle at a time** (successive
sampling with unequal probabilities). If $R$ is the set of particles not drawn
yet, the next particle is $i$ with probability

$$P(\text{next} = i) = \frac{w_i}{\sum_{j \in R} w_j}.$$

**3. The "pull" of a slice.** With $\alpha = 0$ and $r_s$ particles of slice
$s$ still undrawn, the chance that the next particle comes from slice $s$ is

$$P(\text{next from } s) = \frac{r_s / n_s}{\sum_t r_t / n_t},$$

i.e. each slice pulls with the **fraction of its particles that is still
undrawn**. All slices start with pull 1; a small slice loses its pull as it is
emptied; a huge slice (millions) hardly empties and keeps pulling at ~1.

**4. How many particles each slice gives (prediction).** Treating the draws
as continuous, slice $s$ ends with about

$$m_s \approx n_s\left(1 - e^{-\tau / n_s}\right), \qquad \text{with } \tau \text{ chosen so that } \sum_s m_s = N.$$

* small slice ($n_s \ll \tau$): $m_s \approx n_s$ - **all its particles are taken**;
* huge slice ($n_s \gg \tau$): $m_s \approx \tau$ - every large slice gives about the
  **same** number, $\tau$;
* in between, the slice is partly emptied.

*Toy check* (3 slices of 1,000,000 / 10,000 / 100 particles, $N$ = 30,000): the
formula gives $\tau$ = 21,312 and 21,087 / 8,813 / 100; drawing with the
notebook's code gives 21,033-21,075 / 8,825-8,867 / 100. The cell below does
the same check on the real slices.

**How to say it in one sentence:** *"k-means was fitted on a 500,000-particle
subsample drawn without replacement with probability inversely proportional to
the number of particles in the particle's 15° outer-direction sector
($\alpha = 0$), so that every direction sector carries equal weight in the fit;
sectors with fewer particles than their share contribute all of them. All
reported proportions are computed by assigning every particle to its nearest
centroid, i.e. on the full, unweighted population."*
"""),
code(r"""
# prediction (formula 4) vs what the sampling actually drew, alpha = 0
from scipy.optimize import brentq
ns = n_sector[n_sector > 0].astype(float)
tau = brentq(lambda t: (ns * (1 - np.exp(-t / ns))).sum() - N_SUB, 1, 1e9)
m_pred = ns * (1 - np.exp(-tau / ns))
m_real = np.bincount(sector[samples[0.0]], minlength=n_sec)[n_sector > 0]
chk = pd.DataFrame({"particles n_s": ns.astype(int), "predicted m_s": m_pred.round(0).astype(int),
                    "drawn": m_real, "taken (% of slice)": (100 * m_real / ns).round(1)},
                   index=tab.index)
print(f"tau = {tau:,.0f} -> every large slice gives about tau particles")
chk
"""),
md(r"""
### The samples on the map

**Note:** each panel below draws only the **first 30,000** particles of its
500,000-particle sample, so the dots stay readable - every panel has exactly
30,000 dots. With alpha = 0 they are *spread* over many more directions instead
of piled on top of each other in the north-west, which makes the panel look
fuller. The density maps after it use **all 500,000** particles of each sample.
"""),
code(r"""
# the same samples on the map: what k-means 'sees' (30,000 dots per panel, for readability)
fig, axes = plt.subplots(1, 3, figsize=(26, 7), sharex=True, sharey=True)
for ax, a in zip(axes, (1.0, 0.5, 0.0)):
    idx = samples[a][:30_000]
    draw_coast(ax)
    ax.scatter(fit[P.lon_col(R_OUT)].to_numpy()[idx], fit[P.lat_col(R_OUT)].to_numpy()[idx],
               c=[cmap(k) for k in sector[idx]], s=2)
    ax.set_title(f"30,000 particles of the fit sample, alpha = {a:g}: "
                 f"{100 * east[samples[a]].mean():.0f}% eastward")
fig.suptitle("Outer points of the particles k-means is fitted on", y=1.0)
fig.tight_layout(); plt.show()
"""),
md(r"""
### Density of the whole fit sample (all 500,000 particles)

Number of sample particles whose outer point falls in each 0.5° cell (log
colour scale, same scale in the three panels). Total in every panel = 500,000.
With alpha = 1 the north-west cells hold tens of thousands of particles each
and the east is almost empty; with alpha = 0 fewer particles come from the
north-west and the eastern cells fill up - with the **same total**.
"""),
code(r"""
from matplotlib.colors import LogNorm
lon_b = np.arange(-72, -25 + 0.5, 0.5); lat_b = np.arange(-3, 22 + 0.5, 0.5)
lon_out = fit[P.lon_col(R_OUT)].to_numpy(); lat_out = fit[P.lat_col(R_OUT)].to_numpy()
H = {a: np.histogram2d(lon_out[idx], lat_out[idx], bins=[lon_b, lat_b])[0].T for a, idx in samples.items()}
vmax = max(h.max() for h in H.values())
fig, axes = plt.subplots(1, 3, figsize=(26, 7), sharex=True, sharey=True)
for ax, a in zip(axes, (1.0, 0.5, 0.0)):
    draw_coast(ax)
    pcm = ax.pcolormesh(lon_b, lat_b, np.where(H[a] > 0, H[a], np.nan), norm=LogNorm(1, vmax),
                        cmap="viridis", shading="flat", zorder=1)
    idx = samples[a]
    nw = (bearing[idx] < 0).sum(); ea = (bearing[idx] > 0).sum()
    ax.set_title(f"alpha = {a:g}: {len(idx):,} particles in the sample\n"
                 f"west of north {nw:,} ({100 * nw / len(idx):.0f}%), east of north {ea:,} ({100 * ea / len(idx):.0f}%)")
fig.colorbar(pcm, ax=axes, shrink=.8, label="sample particles per 0.5° cell (log)")
fig.suptitle("Outer points of the whole fit sample (500,000 particles in each panel)", y=1.0)
plt.show()
"""),
md(r"""
## 5. What k-means does with each sample

The same fit as v3 (radius weights ~ radius², K = 400) on the three samples
(alpha = 1, 0.5, 0). Each
centroid is given the direction of its own centroid track (crossing -> outer
point). Left: how many of the 400 centroids point into each slice; right: the
centroid tracks.
"""),
code(r"""
X_all = P.build_feature_matrix(fit)
W = P.feature_weight_vector(RADIUS_WEIGHTS)
start_all = fit.cross_lon.to_numpy()
fits = {}
for a in (1.0, 0.5, 0.0):
    idx = samples[a]
    sc = StandardScaler().fit(X_all[idx])
    km = MiniBatchKMeans(n_clusters=K_DEMO, random_state=SEED, batch_size=10000, n_init=10,
                         max_iter=300).fit(sc.transform(X_all[idx]) * W)
    cent = pd.DataFrame(X_all[idx]).groupby(km.labels_).mean().reindex(range(K_DEMO)).to_numpy()
    st = pd.Series(start_all[idx]).groupby(km.labels_).mean().reindex(range(K_DEMO)).to_numpy()
    cb = P.bearing_deg(C.LAT_CROSS, st, cent[:, -2], cent[:, -1])
    fits[a] = dict(km=km, sc=sc, cent=cent, start=st,
                   csec=np.clip(np.floor((cb + 180) / SECTOR_DEG).astype(int), 0, n_sec - 1), east=cb > 0)
    print(f"alpha={a:g}: {int(fits[a]['east'].sum())} of {K_DEMO} centroids point east")

fig = plt.figure(figsize=(20, 18))
for r, a in enumerate((1.0, 0.5, 0.0)):
    ax = fig.add_subplot(3, 2, 2 * r + 1, projection="polar")
    cnt = np.bincount(fits[a]["csec"], minlength=n_sec)
    ax.bar(centers, cnt, width=np.deg2rad(SECTOR_DEG) * .9, color=[cmap(k) for k in range(n_sec)],
           edgecolor="k", lw=.4)
    ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
    ax.set_title(f"alpha = {a:g}: number of centroids per slice ({int(fits[a]['east'].sum())} eastward)", pad=16)
    ax = fig.add_subplot(3, 2, 2 * r + 2)
    draw_coast(ax)
    for c in range(K_DEMO):
        lo = np.r_[fits[a]["start"][c], fits[a]["cent"][c, 1::2]]; la = np.r_[C.LAT_CROSS, fits[a]["cent"][c, 0::2]]
        ax.plot(lo, la, "-", color=cmap(fits[a]["csec"][c]), lw=.8, alpha=.8)
    ax.set_title(f"alpha = {a:g}: the {K_DEMO} centroid tracks, coloured by slice")
fig.tight_layout(); plt.show()
"""),
md(r"""
## 6. Why the reported shares are still the real ones

The balanced sample decides **where the centroids are**. The share of each
cluster or pathway is then measured by giving **every real particle** (here a
random 2 million, unbalanced) its nearest centroid. Below: the share of
particles in eastward clusters - in the balanced fit sample versus among the
real particles. The fit sample over-represents them on purpose; the real share
is what goes into results.
"""),
code(r"""
ps = np.random.default_rng(0).choice(len(fit), 2_000_000, replace=False)
rows = []
for a in (1.0, 0.5, 0.0):
    F = fits[a]
    lab_fit = F["km"].labels_
    lab_all = F["km"].predict(F["sc"].transform(X_all[ps]) * W)
    rows.append({"alpha": a, "eastward centroids": int(F["east"].sum()),
                 "% of FIT SAMPLE in eastward clusters": 100 * F["east"][lab_fit].mean(),
                 "% of REAL particles in eastward clusters": 100 * F["east"][lab_all].mean()})
print(pd.DataFrame(rows).round(2).to_string(index=False))
print("\nThe real share stays ~2-3% in all cases; balancing only gives that water more, and more distinct, clusters.")
"""),
md(r"""
## 7. Background and references

**What the method is, in standard terms.** Fitting k-means on this sample is
equivalent to *weighted k-means* with each particle weighted by
1 / (number of particles in its direction slice); the shares are then
re-weighted to the real population by labelling all particles. It combines:

* **Quantization theory** - with many clusters, k-means centres follow the data
  density to a power below 1, so rare regions get few centres
  (Gersho 1979, *IEEE Trans. Inf. Theory* 25(4); Graf & Luschgy 2000,
  *Foundations of Quantization for Probability Distributions*, LNM 1730).
* **Stratified sampling with unequal probabilities, re-weighted to the
  population** (Cochran 1977, *Sampling Techniques*, 3rd ed.).
* **Re-balancing rare classes before learning** (He & Garcia 2009, *IEEE
  TKDE* 21(9); Chawla et al. 2002, SMOTE, *JAIR* 16).

**Closest Lagrangian precedent found** (literature search 2026-10-21): Jutras
et al. (2024), *Machine learning-based clustering of oceanic Lagrangian
particles: identification of the main pathways of the Labrador Current*,
JAMES, doi:10.1029/2023MS003902 - k-means++ on model particles, more clusters
than pathways, then expert merging (the same workflow as 1.5); they subsample
*equally per time period*, i.e. balance in time. No study was found that
balances by direction/region to keep rare pathways, so this is a new choice
that must be stated and justified in the methods.

**Checks done in this project:** alpha = 1 / 0.5 / 0 compared (v2.1.5 sweep):
without balancing at most ~18 pathways >= 400 km apart, with alpha = 0 ~26,
and 95-97% of them reappear in independent fits - the extra pathways are not
noise from over-sampling. Choices that could change details: the slice width
(15°) and what defines the "direction" (crossing -> 2000 km / last position).

**Open physical point.** Classic observations (Muller-Karger, McClain &
Richardson 1988, *Nature* 333, 56-59) show a large part of the Amazon water
going **east** around the NBC retroflection into the NECC from about June to
January. In run_2 only ~2.4% of the particles have an eastward direction by
this definition. Part of that may be the definition (water that retroflects,
is caught in rings and moves north-west counts as north-west) or the 185-day
tracks - worth checking before interpreting pathway shares.
"""),
])

# =========================================================================== #
# 1.7 - particles that never cross 2.5N
# =========================================================================== #
save("1.7_NoCross_clustering.ipynb", [
md(r"""
# 1.7 - Clustering the particles that never cross 2.5N

About **2.3% of the particles (~356,000) never cross 2.5N** (status `no_cross`)
and are left out of 1.5 / v3. This notebook clusters them on their own,
step by step, with the same tools as v3.1.5:

1. read their daily tracks from all stores (once, then cached);
2. explore where they are released, how far and where they go;
3. choose and build the features;
4. K sweep: how many separated pathways, and do they come back in
   independent fits;
5. final fit: clusters, pathways, shares;
6. hierarchical view (tree + map);
7. real tracks per pathway;
8. seasonality (release month).

**What they are (all 356,541 particles, 2026-10-22):** released in two areas -
the Pará estuary (~48.7-48.2W, 1.5S-0.5S) and the Amazon channels north of
Marajó Island (~51-49W, 0-1.5N) - mostly in July-November (Aug and Sep ~23%
each). They move little: median distance from release ~35 km at day 30,
~55 km at day 120, ~145 km at day 184; 41% ever get 200 km and 12% 300 km
away (section 2).
"""),
code(BOOT + r"""
import time
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.feature as cfeature
from joblib import Parallel, delayed
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import squareform
"""),
params_code(r"""
DAYS_NC = [15, 30, 60, 90, 120, 150, 180]   # positions at these days after release are the features
DAY_WEIGHTS_NC = None            # None = every day equal; or {15: .., 30: .., ...}
K_SWEEP = [5, 10, 15, 20, 30, 40, 60, 80]
SEEDS = [42, 1, 7]               # independent fits, each on a different random 80% of the particles
PATHWAY_SEP_KM = 50              # two pathways differ if their tracks are >= this far apart (mean over DAYS_NC)
MATCH_KM = 25                    # a pathway is reproduced if another fit has one within this distance
K = None                         # final K; None -> chosen from the sweep
REBUILD_CACHE = False            # True -> re-read the tracks from all stores
SAVE_MODEL = False
"""),
md(r"""
## 1. Daily tracks of the never-crossing particles

They are listed in `features.parquet` (status `no_cross`, with `store` /
`row` / `traj`). Their tracks are read from every store, one position per day
(every 4th 6-hourly output), and cached in `data/no_cross/`, so later runs
skip this step (set `REBUILD_CACHE = True` to redo it).
"""),
code(r"""
NC_DIR = C.DATA_DIR / "no_cross"; NC_DIR.mkdir(exist_ok=True)
CACHE_TRK, CACHE_META = NC_DIR / "daily_tracks.npz", NC_DIR / "meta.parquet"
N_DAYS = 185                                   # days 0 .. 184 after release

def read_store(path, rows, trajs):
    ds = xr.open_zarr(path)
    got = ds.trajectory.values[rows]
    assert np.array_equal(got, trajs), f"{path.name}: Parcels IDs do not match - re-run 01"
    out = []
    for v in ("lat", "lon"):
        a = ds[v].values[rows][:, ::4][:, :N_DAYS].astype(np.float32)
        if a.shape[1] < N_DAYS:
            a = np.pad(a, ((0, 0), (0, N_DAYS - a.shape[1])), constant_values=np.nan)
        out.append(a)
    t0 = ds.time.values[rows, 0]
    return out[0], out[1], t0

if REBUILD_CACHE or not CACHE_TRK.exists():
    t0_ = time.time()
    f = pd.read_parquet(C.FEATURES_FILE, columns=["trajectory_id", "store", "row", "traj", "status"])
    nc = f[f.status == "no_cross"].drop(columns="status").reset_index(drop=True); del f
    paths = C.store_paths_by_name()
    groups = list(nc.groupby("store", observed=True))
    res = Parallel(n_jobs=int(os.environ.get("SLURM_CPUS_PER_TASK", 16)), backend="loky")(
        delayed(read_store)(paths[name], g.row.to_numpy(), g.traj.to_numpy()) for name, g in groups)
    meta = pd.concat([g for _, g in groups], ignore_index=True)
    LAT = np.concatenate([r[0] for r in res]); LON = np.concatenate([r[1] for r in res])
    meta["release_time"] = pd.to_datetime(np.concatenate([r[2] for r in res]))
    np.savez_compressed(CACHE_TRK, lat=LAT, lon=LON)
    meta.to_parquet(CACHE_META, index=False)
    print(f"read {len(meta):,} tracks from {len(groups)} stores in {(time.time() - t0_) / 60:.1f} min")
else:
    _z = np.load(CACHE_TRK); LAT, LON = _z["lat"], _z["lon"]
    meta = pd.read_parquet(CACHE_META)
    print("loaded cache:", CACHE_TRK)
# a deleted / missing position keeps the last known one (tracks are 185 days for all of them)
LAT = pd.DataFrame(LAT).ffill(axis=1).to_numpy(np.float32)
LON = pd.DataFrame(LON).ffill(axis=1).to_numpy(np.float32)
meta["release_month"] = meta.release_time.dt.month
print(f"{len(meta):,} never-crossing particles, {LAT.shape[1]} daily positions each")
"""),
md(r"""
## 2. Explore: where are they released, how far and where do they go?
"""),
code(r"""
_coast = []
for geom in cfeature.COASTLINE.with_scale("10m").geometries():
    for line in getattr(geom, "geoms", [geom]):
        x, y = np.asarray(line.xy[0]), np.asarray(line.xy[1])
        if ((x > -56) & (x < -40) & (y > -5) & (y < 8)).any():
            _coast.append((x, y))
ZOOM = (np.nanpercentile(LON, .5) - .5, np.nanpercentile(LON, 99.5) + .5,
        np.nanpercentile(LAT, .5) - .5, np.nanpercentile(LAT, 99.5) + .5)
def draw_coast(ax):
    for x, y in _coast:
        ax.plot(x, y, "-", color="0.55", lw=.6, zorder=0)
    ax.axhline(C.LAT_CROSS, color="k", ls="--", lw=.6); ax.axhline(0, color="0.7", lw=.5)
    ax.set_xlim(ZOOM[0], ZOOM[1]); ax.set_ylim(ZOOM[2], ZOOM[3]); ax.set_aspect("equal")

dist = P.haversine_km(LAT[:, :1], LON[:, :1], LAT, LON)          # km from release, every day
from matplotlib.colors import LogNorm
lon_b = np.arange(ZOOM[0], ZOOM[1] + .1, .1); lat_b = np.arange(ZOOM[2], ZOOM[3] + .1, .1)
fig, ax = plt.subplots(1, 3, figsize=(22, 6.5))
draw_coast(ax[0])
h0 = np.histogram2d(LON[:, 0], LAT[:, 0], bins=[lon_b, lat_b])[0].T
ax[0].pcolormesh(lon_b, lat_b, np.where(h0 > 0, h0, np.nan), norm=LogNorm(), cmap="viridis")
ax[0].set_title("release positions (count per 0.1° cell)")
draw_coast(ax[1])
ha = np.histogram2d(LON[:, 1:].ravel(), LAT[:, 1:].ravel(), bins=[lon_b, lat_b])[0].T
ax[1].pcolormesh(lon_b, lat_b, np.where(ha > 0, ha, np.nan), norm=LogNorm(), cmap="magma_r")
ax[1].set_title("all daily positions (days 1-184): where the water spends its time")
draw_coast(ax[2])
he = np.histogram2d(LON[:, -1], LAT[:, -1], bins=[lon_b, lat_b])[0].T
ax[2].pcolormesh(lon_b, lat_b, np.where(he > 0, he, np.nan), norm=LogNorm(), cmap="viridis")
ax[2].set_title("positions at day 184 (end of the track)")
fig.tight_layout(); plt.show()

days = np.arange(LAT.shape[1])
q = np.nanpercentile(dist, [10, 25, 50, 75, 90], axis=0)
fig, ax = plt.subplots(1, 3, figsize=(20, 4.5))
ax[0].fill_between(days, q[0], q[4], color="0.88", label="10-90%")
ax[0].fill_between(days, q[1], q[3], color="0.7", label="25-75%")
ax[0].plot(days, q[2], "k-", label="median")
ax[0].set_xlabel("days after release"); ax[0].set_ylabel("km from release"); ax[0].legend(frameon=False)
ax[0].set_title("distance from the release point")
R = np.arange(10, 501, 10)
ax[1].plot(R, [100 * (np.nanmax(dist, 1) >= r).mean() for r in R], "k-")
ax[1].set_xlabel("radius around the release point [km]"); ax[1].set_ylabel("% that ever get this far")
ax[1].set_title("why not circles: few get far"); ax[1].grid(color="0.92")
mc = meta.release_month.value_counts().reindex(range(1, 13), fill_value=0)
ax[2].bar(mc.index, 100 * mc / mc.sum(), color="tab:blue"); ax[2].set_xticks(range(1, 13))
ax[2].set_xlabel("release month"); ax[2].set_ylabel("% of these particles")
ax[2].set_title("when they are released")
fig.tight_layout(); plt.show()
for r in (50, 100, 200, 300):
    print(f"ever {r:3d} km from release: {100 * (np.nanmax(dist, 1) >= r).mean():5.1f}%")
"""),
md(r"""
## 3. Features: positions at fixed days after release

The 2.5N-crossing clock and circles of v3 do not fit these particles: they
never cross, and few move far (see the curve above - circles of 100-200 km
would leave a quarter to a half of them as `partial`). But **all their tracks
run the full 185 days**, so the positions at fixed days after release exist
for every particle - no stand-ins - and also record **how long the water
stays** near the estuary, which is the main thing that differs between them.

Features: `[lat, lon]` at the days in `DAYS_NC`, each column standardized
(mean 0, std 1) and optionally weighted per day (`DAY_WEIGHTS_NC`), as in v3.
No balanced sampling: all ~356,000 particles fit in one k-means run.
"""),
code(r"""
day_idx = np.array(DAYS_NC)
X = np.column_stack([a for d in day_idx for a in (LAT[:, d], LON[:, d])]).astype(np.float64)
ok = np.isfinite(X).all(axis=1)
print(f"{ok.sum():,} of {len(X):,} particles have all features")
X, meta_ok = X[ok], meta[ok].reset_index(drop=True)
LAT_ok, LON_ok = LAT[ok], LON[ok]
wd = DAY_WEIGHTS_NC or {d: 1.0 for d in DAYS_NC}
Wd = np.array([np.sqrt(wd[d]) for d in DAYS_NC for _ in range(2)])
print("days:", DAYS_NC, "| weights:", wd)

def track_dist(A, B):            # mean haversine distance between two sets of tracks over DAYS_NC (km)
    nd = A.shape[1] // 2
    return sum(P.haversine_km(A[:, None, 2*j], A[:, None, 2*j+1], B[None, :, 2*j], B[None, :, 2*j+1])
               for j in range(nd)) / nd

def fit_k(k, rows, seed, n_init=10):
    sc = StandardScaler().fit(X[rows])
    km = MiniBatchKMeans(n_clusters=k, random_state=seed, batch_size=10000, n_init=n_init,
                         max_iter=300).fit(sc.transform(X[rows]) * Wd)
    cent = pd.DataFrame(X[rows]).groupby(km.labels_).mean().reindex(range(k)).to_numpy()
    return km, sc, cent

def pathways(cent):
    g = fcluster(linkage(squareform(track_dist(cent, cent), checks=False), "complete"),
                 t=PATHWAY_SEP_KM, criterion="distance") - 1
    return g, np.array([cent[g == i].mean(axis=0) for i in range(g.max() + 1)])
"""),
md(r"""
## 4. K sweep: how many separated pathways, and are they reproducible?

For each K, three fits on three different random 80% subsets (seeds
`SEEDS`). Centroids closer than `PATHWAY_SEP_KM` (mean over the days) are
grouped into one pathway; a pathway counts as **reproducible** if a pathway
within `MATCH_KM` appears in both other fits. The thresholds are smaller than
in v3 (400 / 200 km) because these particles move ~50-300 km in total.
"""),
code(r"""
rows_all = np.arange(len(X))
runs, recs = {}, []
for k in K_SWEEP:
    for s in SEEDS:
        rows = np.random.default_rng(s).choice(rows_all, int(.8 * len(rows_all)), replace=False)
        km_s, sc_s, cent = fit_k(k, rows, s)
        g, pt = pathways(cent)
        runs[(k, s)] = pt
        recs.append(dict(K=k, seed=s, pathways=len(pt)))
    for s in SEEDS:
        ok_ = np.all([track_dist(runs[(k, s)], runs[(k, o)]).min(axis=1) < MATCH_KM for o in SEEDS if o != s], axis=0)
        r = next(r for r in recs if r["K"] == k and r["seed"] == s)
        r["reproduced_%"] = round(100 * ok_.mean()); r["reproducible"] = int(ok_.sum())
    print(f"K={k:3d}: " + ", ".join(f"{r['pathways']} ({r['reproducible']} reproducible)"
                                    for r in recs if r["K"] == k), flush=True)
sweep = pd.DataFrame(recs)
s_ = sweep.groupby("K").agg(p=("pathways", "mean"), rp=("reproducible", "mean"), rpmin=("reproducible", "min"),
                            rpmax=("reproducible", "max"), r=("reproduced_%", "mean"))
fig, ax = plt.subplots(1, 2, figsize=(13, 4))
ax[0].plot(s_.index, s_.p, "o--", color="0.5", label="all pathways")
ax[0].fill_between(s_.index, s_.rpmin, s_.rpmax, color="lightblue", alpha=.5, lw=0)
ax[0].plot(s_.index, s_.rp, "o-", color="tab:blue", label="reproducible pathways")
ax[0].set_xlabel("K"); ax[0].set_ylabel(f"pathways >= {PATHWAY_SEP_KM} km apart"); ax[0].legend(frameon=False)
ax[1].plot(s_.index, s_.r, "o-", color="tab:blue"); ax[1].axhline(95, color="0.5", ls="--", lw=.8)
ax[1].set_xlabel("K"); ax[1].set_ylabel("% reproduced"); ax[1].set_ylim(0, 102)
for a in ax: a.grid(color="0.92")
fig.tight_layout(); plt.show()
good = s_[s_.r >= 95]
K_AUTO = int((good if len(good) else s_).sort_values(["rp", "r"], ascending=[False, False]).index[0])
print(s_.round(1).to_string())
print(f"suggested K = {K_AUTO}: {s_.loc[K_AUTO, 'rp']:.1f} reproducible pathways ({s_.loc[K_AUTO, 'r']:.0f}% reproduced)")
if K is None:
    K = K_AUTO
print("K used below:", K)
"""),
md(r"""
## 5. Final fit: clusters, pathways and their shares

Fit on all particles. Every particle gets a cluster, so the shares are the
real ones directly (no balanced sample here).
"""),
code(r"""
km, scaler, cent_deg = fit_k(K, rows_all, SEEDS[0], n_init=20)
labels = km.labels_
sizes = np.bincount(labels, minlength=K)
PATH_OF, ptrack = pathways(cent_deg)
n_path = len(ptrack)
share_cl = 100 * sizes / sizes.sum()
share = np.array([share_cl[PATH_OF == i].sum() for i in range(n_path)])
rel_lon = pd.Series(LON_ok[:, 0]).groupby(labels).mean().reindex(range(K)).to_numpy()
rel_lat = pd.Series(LAT_ok[:, 0]).groupby(labels).mean().reindex(range(K)).to_numpy()
def cl_track(c):                 # release point -> positions at DAYS_NC
    return np.r_[rel_lon[c], cent_deg[c, 1::2]], np.r_[rel_lat[c], cent_deg[c, 0::2]]
def pw_track(i):                 # pathway mean track weighted by cluster size
    m = PATH_OF == i
    tr = np.average(cent_deg[m], axis=0, weights=sizes[m])
    return np.r_[np.average(rel_lon[m], weights=sizes[m]), tr[1::2]], np.r_[np.average(rel_lat[m], weights=sizes[m]), tr[0::2]]
end_km = np.array([P.haversine_km(pw_track(i)[1][0], pw_track(i)[0][0], pw_track(i)[1][-1], pw_track(i)[0][-1])
                   for i in range(n_path)])                   # release -> last day, km
ptab = pd.DataFrame({"clusters": np.bincount(PATH_OF, minlength=n_path), "% of particles": share.round(2),
                     f"lat day {DAYS_NC[-1]}": [pw_track(i)[1][-1].round(2) for i in range(n_path)],
                     f"lon day {DAYS_NC[-1]}": [pw_track(i)[0][-1].round(2) for i in range(n_path)],
                     f"km from release at day {DAYS_NC[-1]}": end_km.round(0)},
                    index=pd.Index(range(n_path), name="pathway"))
print(f"fit K={K} on {len(X):,} particles | {n_path} pathways >= {PATHWAY_SEP_KM} km apart | sizes {sizes.min()}..{sizes.max()}")
ptab.sort_values("% of particles", ascending=False)
"""),
code(r"""
pcmap = plt.get_cmap("tab20", max(n_path, 3))
fig, ax = plt.subplots(1, 2, figsize=(20, 8))
draw_coast(ax[0])
for c in range(K):
    lo, la = cl_track(c)
    ax[0].plot(lo, la, "-", color=pcmap(PATH_OF[c]), lw=.8, alpha=.7)
ax[0].set_title(f"All {K} cluster tracks (release -> days {DAYS_NC}), coloured by pathway")
draw_coast(ax[1])
for i in range(n_path):
    lo, la = pw_track(i)
    ax[1].plot(lo, la, ".-", color=pcmap(i), lw=1 + 4 * np.sqrt(share[i] / share.max()))
    ax[1].text(lo[-1], la[-1], f" {i} ({share[i]:.2g}%)", fontsize=8)
ax[1].set_title(f"{n_path} pathways (mean tracks, line width ~ share of particles)")
fig.tight_layout(); plt.show()
"""),
code(r"""
# persist the fit (only when SAVE_MODEL is True)
import joblib, json
if SAVE_MODEL:
    MODEL_DIR = C.MODELS_DIR / f"no_cross_1.7_k{K}"; MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(km, MODEL_DIR / f"kmeans_k{K}.pkl"); joblib.dump(scaler, MODEL_DIR / "scaler.pkl")
    np.save(MODEL_DIR / "weights_W.npy", Wd); np.save(MODEL_DIR / "pathway_of_cluster.npy", PATH_OF)
    meta_ok[["trajectory_id", "store", "row", "traj", "release_time"]].assign(
        cluster=labels, pathway=PATH_OF[labels]).to_parquet(MODEL_DIR / "labels.parquet", index=False)
    (MODEL_DIR / "fit_metadata.json").write_text(json.dumps(dict(
        source_notebook="1.7_NoCross_clustering.ipynb", K=K, DAYS_NC=DAYS_NC,
        DAY_WEIGHTS_NC={str(k): v for k, v in wd.items()}, PATHWAY_SEP_KM=PATHWAY_SEP_KM,
        n_pathways=int(n_path), n_particles=int(len(X))), indent=2))
    print("saved ->", MODEL_DIR)
else:
    print("SAVE_MODEL is False -> nothing written")
"""),
md(r"""
## 6. Hierarchical view
Complete-linkage tree of the K cluster tracks (same distance as the
pathways). Left: the tree with the `PATHWAY_SEP_KM` cut; right: the clusters
coloured by the groups of a cut into `N_GROUPS` groups.
"""),
code(r"""
N_GROUPS = 6
Z = linkage(squareform(track_dist(cent_deg, cent_deg), checks=False), "complete")
hg = fcluster(Z, t=N_GROUPS, criterion="maxclust") - 1
fig, ax = plt.subplots(1, 2, figsize=(22, 7), gridspec_kw={"width_ratios": [1, 1.1]})
dendrogram(Z, ax=ax[0], truncate_mode="lastp", p=min(40, K), color_threshold=PATHWAY_SEP_KM,
           leaf_rotation=90, leaf_font_size=7)
ax[0].axhline(PATHWAY_SEP_KM, color="k", ls="--", lw=.8); ax[0].set_ylabel("complete-linkage distance (km)")
ax[0].set_title(f"{K} clusters -> {n_path} pathways (cut at {PATHWAY_SEP_KM} km)")
gcm = plt.get_cmap("tab10", max(N_GROUPS, 3))
draw_coast(ax[1])
for c in range(K):
    lo, la = cl_track(c)
    ax[1].plot(lo, la, "-", color=gcm(hg[c]), lw=.8, alpha=.6)
for gi in range(N_GROUPS):
    m = hg == gi
    tr = np.average(cent_deg[m], axis=0, weights=sizes[m])
    lo = np.r_[np.average(rel_lon[m], weights=sizes[m]), tr[1::2]]; la = np.r_[np.average(rel_lat[m], weights=sizes[m]), tr[0::2]]
    ax[1].plot(lo, la, ".-", color=gcm(gi), lw=4)
    ax[1].text(lo[-1], la[-1], f" {gi} ({share_cl[m].sum():.2g}%)", fontsize=9, fontweight="bold", color=gcm(gi))
ax[1].set_title(f"clusters cut into {N_GROUPS} hierarchical groups (thick = group mean track)")
fig.tight_layout(); plt.show()
"""),
md(r"""
## 7. Real tracks per pathway
Up to `TRACKS_PER_PANEL` random member particles of each pathway (all days),
with the pathway mean track in orange.
"""),
code(r"""
TRACKS_PER_PANEL = 40
rng = np.random.default_rng(0)
pw_lab = PATH_OF[labels]
order = np.argsort(-share)
ncol = 4; nrow = int(np.ceil(n_path / ncol))
fig, axes = plt.subplots(nrow, ncol, figsize=(4.8 * ncol, 3.8 * nrow), squeeze=False, sharex=True, sharey=True)
for j, i in enumerate(order):
    ax = axes[j // ncol][j % ncol]
    draw_coast(ax)
    mem = np.where(pw_lab == i)[0]
    for r in rng.choice(mem, min(TRACKS_PER_PANEL, len(mem)), replace=False):
        ax.plot(LON_ok[r], LAT_ok[r], "-", color="tab:blue", lw=.4, alpha=.35)
    lo, la = pw_track(i)
    ax.plot(lo, la, ".-", color="darkorange", lw=2.5, zorder=3)
    ax.set_title(f"pathway {i}: {share[i]:.2g}% ({len(mem):,} particles)", fontsize=9)
for j in range(n_path, nrow * ncol):
    axes[j // ncol][j % ncol].axis("off")
fig.suptitle("Real tracks (blue, days 0-184) and pathway mean track (orange)", y=1.0)
fig.tight_layout(); plt.show()
"""),
md(r"""
## 8. Seasonality: which pathway, by release month
Share of each month's never-crossing particles in each pathway (only months
with at least 1,000 particles).
"""),
code(r"""
mt = pd.crosstab(meta_ok.release_month, pw_lab)
mt = mt[mt.sum(axis=1) >= 1000]
mp = mt.div(mt.sum(axis=1), axis=0) * 100
fig, ax = plt.subplots(figsize=(11, 5))
bottom = np.zeros(len(mp))
for i in order:
    vals = mp.get(i, pd.Series(0, index=mp.index)).to_numpy()
    ax.bar(mp.index.astype(str), vals, bottom=bottom, color=pcmap(i), label=f"{i} ({share[i]:.2g}%)")
    bottom += vals
ax.set_xlabel("release month"); ax.set_ylabel("% of that month's never-crossing particles")
ax.legend(ncol=2, fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left", title="pathway")
fig.tight_layout(); plt.show()
print("particles per release month:", mt.sum(axis=1).to_dict())
"""),
])

# =========================================================================== #
# 1.6 - tropical / eastward sub-clustering (two-stage)
# =========================================================================== #
save("1.6_Tropical_subclustering.ipynb", [
md(r"""
# 1.6 - Tropical (eastward) sub-clustering (two-stage)

The eastward retroflection / tropical pathway is a small share of the particles,
so the global k-means (notebook 1.5) gives it only a few clusters - k-means
spends clusters where the data is dense. **Two stages:** pick out the
eastward particles first, then cluster only them with their own K.

**Selection by direction (not by end point).** For each particle, take its exit
point at `GATE_R` km (default 1000 km) and the compass direction from its own
2.5N crossing point to that exit (0 = N, 90 = E, -90 = W). Particles whose
direction is inside `BEARING_RANGE` are kept. Almost every particle reaches
1000 km (~97-99%), so this loses far fewer particles than a rule on the
outermost radius: eastward particles often end their track before 2000 km
(`partial`), and are kept here (`FIT_STATUS`), with their last position
standing in for the radii they did not reach.

In a first test most of the eastward subset was `partial` (few reach 1500 km,
almost none 2000 km), so their 1500 / 2000 km features are mostly the end of
the track. The check after the selection flags such radii; setting their
weight to 0 clusters on the radii the subset really reaches.

**One particle as an example:** it crosses 2.5N at 49W, turns back east at
about 7N and is 1000 km from its crossing point near 8N 41W. The direction
crossing -> exit is about 60 (north-east), inside the default (0, 180), so it is
kept. A particle that goes along the shelf to the north-west exits at about
-45 and is left out.

Workflow, as in 1.5: tune the settings, run top to bottom, give each
sub-cluster a letter in `ASSIGN`, set `SAVE_MODEL = True` and re-run the save
cells to write the model and the per-particle sub-labels.
"""),
code(BOOT + r"""
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
"""),
params_code(r"""
K_TROPICAL = 20                      # clusters for the eastward subset only
GATE_R = 1000                        # radius whose exit direction selects (one of C.RADII_KM)
BEARING_RANGE = (0, 180)             # kept directions, from-to in deg clockwise from N (0 N, 90 E, -90 W)
FIT_STATUS = ["complete", "partial"] # statuses kept (partial: track ended before a larger radius)
SAVE_MODEL = False                   # True -> write model + sub-labels (save cells)
"""),
code(r"""
# per-radius weights tuned HERE for the subset (None -> config.RADIUS_WEIGHTS).
# 0 switches a radius off: use it for radii most of the subset never reaches
# (their value is only the last position of the track - see the check below).
RADIUS_WEIGHTS = {200: 1.0, 500: 1.0, 1000: 1.0, 1500: 1.0, 2000: 1.0}

assert GATE_R in C.RADII_KM, f"GATE_R must be one of {C.RADII_KM}"
_wr = RADIUS_WEIGHTS if RADIUS_WEIGHTS is not None else C.RADIUS_WEIGHTS
W = P.feature_weight_vector(_wr)
print(f"K_TROPICAL: {K_TROPICAL} | gate: direction at {GATE_R} km in {BEARING_RANGE} "
      f"| statuses: {FIT_STATUS} | weights: {_wr}")
"""),
md(r"""
## Select the eastward subset

The direction is computed from the features file (`cross_lat/lon` and the exit
point at `GATE_R`), so no Zarr store is read. The histogram shows all particles
that reached `GATE_R`, with the kept range shaded - use it to set
`BEARING_RANGE`.
"""),
code(r"""
features = pd.read_parquet(C.FEATURES_FILE)
cand = features[features.status.isin(FIT_STATUS)
                & features[P.days_col(GATE_R)].notna()].copy()     # really reached GATE_R
cand["bearing"] = P.bearing_deg(cand.cross_lat, cand.cross_lon,
                                cand[P.lat_col(GATE_R)], cand[P.lon_col(GATE_R)])
keep = cand.bearing.between(*BEARING_RANGE)
trop = cand[keep].reset_index(drop=True)

n_lab = features.status.isin(["complete", "partial"]).sum()
print(f"reached {GATE_R} km: {len(cand):,} | kept (direction in {BEARING_RANGE}): "
      f"{len(trop):,} = {100*len(trop)/len(cand):.2f}% of them, "
      f"{100*len(trop)/n_lab:.2f}% of all labelled particles")
print("status in the subset:", trop.status.value_counts().to_dict())
for r in C.RADII_KM:
    got = 100 * trop[P.days_col(r)].notna().mean()
    warn = (f"   <-- mostly last-position stand-ins; consider RADIUS_WEIGHTS[{r}] = 0"
            if got < 50 and _wr[r] > 0 else "")
    print(f"  reached {r:5d} km: {got:5.1f}% of the subset (weight {_wr[r]}){warn}")

fig, ax = plt.subplots(figsize=(9, 3.2))
ax.hist(cand.bearing, bins=np.arange(-180, 181, 5), color="0.5")
ax.axvspan(*BEARING_RANGE, color="green", alpha=.15, label="kept")
ax.set_yscale("log")
ax.set_xticks([-180, -135, -90, -45, 0, 45, 90, 135, 180])
ax.set_xticklabels(["S", "SW", "W", "NW", "N", "NE", "E", "SE", "S"])
ax.set_xlabel(f"direction crossing point -> {GATE_R} km exit"); ax.set_ylabel("particles (log)")
ax.legend(frameon=False); fig.tight_layout(); plt.show()
"""),
md(r"""
## Cheap coastline and the gate drawn on the maps
The `GATE_R` circle around the mean crossing point of the subset, green over
the kept directions (each particle really uses its own crossing point).
"""),
code(REFS + r"""
import cartopy.feature as cfeature
lon_lim = (C.DOMAIN["lon_min"], C.DOMAIN["lon_max"])
lat_lim = (C.DOMAIN["lat_min"], C.DOMAIN["lat_max"])

_coast = []
for geom in cfeature.COASTLINE.with_scale("110m").geometries():
    for line in getattr(geom, "geoms", [geom]):
        _coast.append((np.asarray(line.xy[0]), np.asarray(line.xy[1])))

def draw_coast(ax):
    for x, y in _coast:
        ax.plot(x, y, "-", color="0.75", lw=.4, zorder=0)
    ax.set_xlim(*lon_lim); ax.set_ylim(*lat_lim)

_gla, _glo = P.circle_latlon(C.LAT_CROSS, float(trop.cross_lon.mean()), GATE_R)   # point i = bearing i deg
_gb = np.arange(_gla.size); _gb = np.where(_gb > 180, _gb - 360, _gb)
_gin = (_gb >= BEARING_RANGE[0]) & (_gb <= BEARING_RANGE[1])

def draw_gate(ax):
    ax.plot(_glo, _gla, "-", color="0.6", lw=.6, zorder=1)
    ax.plot(np.where(_gin, _glo, np.nan), np.where(_gin, _gla, np.nan), "-",
            color="green", lw=1.6, zorder=1)
print("coastline segments:", len(_coast))
"""),
code(r"""
# where the kept / left-out particles exit the GATE_R circle (random 20k)
s = cand.sample(min(20000, len(cand)), random_state=C.RANDOM_STATE)
k = s.bearing.between(*BEARING_RANGE)
fig, ax = plt.subplots(figsize=(9, 5))
draw_coast(ax); draw_refs(ax); draw_gate(ax)
ax.scatter(s.loc[~k, P.lon_col(GATE_R)], s.loc[~k, P.lat_col(GATE_R)], s=2, color="0.6",
           label="left out")
ax.scatter(s.loc[k, P.lon_col(GATE_R)], s.loc[k, P.lat_col(GATE_R)], s=4, color="green",
           label="kept")
ax.legend(markerscale=4, loc="lower left")
ax.set_title(f"exit points at {GATE_R} km (random {len(s):,}); green arc = kept directions")
fig.tight_layout(); plt.show()
"""),
md(r"""
## Fit k-means on the subset
Small subset -> plain `KMeans`. Standardize each column on the subset, apply the
radius weights, fit.
"""),
code(r"""
K = K_TROPICAL
X_raw  = P.build_feature_matrix(trop)
scaler = StandardScaler().fit(X_raw)
X_sub  = scaler.transform(X_raw) * W

km = KMeans(n_clusters=K, random_state=C.RANDOM_STATE, n_init=10)
labels = km.fit_predict(X_sub)
sizes  = np.bincount(labels, minlength=K)

# centroids in degrees = mean member position per radius (same as undoing the
# scaling when every weight > 0, and still defined for radii with weight 0)
cent_deg  = pd.DataFrame(X_raw).groupby(labels).mean().reindex(range(K)).to_numpy()
start_lon = trop.groupby(labels).cross_lon.mean().reindex(range(K)).to_numpy()
def centroid_track(c):
    return (np.r_[start_lon[c], cent_deg[c, 1::2]],
            np.r_[C.LAT_CROSS, cent_deg[c, 0::2]])
print(f"fit k={K} on {len(trop):,} eastward particles | sizes {sizes.min()}..{sizes.max()}")
"""),
code(r"""
# Persist THIS fit (only when SAVE_MODEL is True).  The subsample labels keep
# store / row / traj, so every particle can be found again.
import joblib, json
MODEL_DIR = C.MODELS_DIR / f"tropical_1.6_k{K}"
if SAVE_MODEL:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(km, MODEL_DIR / f"kmeans_k{K}.pkl")
    joblib.dump(scaler, MODEL_DIR / "scaler.pkl")
    np.save(MODEL_DIR / "weights_W.npy", W)
    np.save(MODEL_DIR / "centroids_deg.npy", cent_deg)
    (MODEL_DIR / "fit_metadata.json").write_text(json.dumps(dict(
        source_notebook="1.6_Tropical_subclustering.ipynb", K=K, LAT_CROSS=C.LAT_CROSS,
        GATE_R=GATE_R, BEARING_RANGE=list(BEARING_RANGE), FIT_STATUS=FIT_STATUS,
        RADII_KM=C.RADII_KM, RADIUS_WEIGHTS={str(k): v for k, v in _wr.items()},
        RANDOM_STATE=C.RANDOM_STATE, n_fitted=int(len(trop)),
        cluster_sizes=sizes.tolist()), indent=2))
    print("saved model ->", MODEL_DIR)
else:
    print("SAVE_MODEL is False -> nothing written")
"""),
md(r"""
## Read a few full member trajectories per sub-cluster
By `store` / `row`, checked against `traj`; each store opened once.
"""),
code(r"""
MEMBERS_PER_PANEL = 20
N_IO_THREADS = int(os.environ.get("SLURM_CPUS_PER_TASK", 16))

memdf = trop[["trajectory_id", "store", "row", "traj", "cross_obs"]].assign(lab=labels)
pick = pd.concat([d.sample(min(MEMBERS_PER_PANEL, len(d)), random_state=C.RANDOM_STATE)
                  for _, d in memdf.groupby("lab")], ignore_index=True)
paths = P.read_paths(pick, n_jobs=N_IO_THREADS)          # trajectory_id -> (lon, lat)
cross_obs = dict(zip(pick.trajectory_id, pick.cross_obs))
members = {c: pick.loc[pick.lab == c, "trajectory_id"].to_numpy() for c in range(K)}
print(f"read {len(paths):,} full trajectories from {pick.store.nunique()} stores")
"""),
md(r"""
## The grid - one panel per sub-cluster
Orange = centroid (mean crossing point -> exit at each radius), blue = member
tracks after the crossing, grey = before; green arc = the kept directions.
"""),
code(r"""
NCOL = 5

def draw_cluster(ax, c):
    draw_coast(ax); draw_gate(ax)
    for tid in members[c]:
        lo, la = paths[int(tid)]
        k0 = cross_obs[tid]
        ax.plot(lo[:k0 + 1], la[:k0 + 1], "-", color="0.6", lw=.4, alpha=.4)
        m = ~(np.isnan(lo[k0:]) | np.isnan(la[k0:]))
        ax.plot(lo[k0:][m], la[k0:][m], "-", color="blue", lw=.4, alpha=.35)
    clo, cla = centroid_track(c)
    ax.plot(clo, cla, ".-", color="darkorange", lw=2, zorder=3)
    ax.plot(clo[-1], cla[-1], "o", color="darkorange", mec="k", ms=6, zorder=4)

nrow = int(np.ceil(K / NCOL))
fig, axes = plt.subplots(nrow, NCOL, figsize=(3.2 * NCOL, 2.5 * nrow),
                         squeeze=False, sharex=True, sharey=True)
for c in range(K):
    ax = axes[c // NCOL][c % NCOL]
    draw_cluster(ax, c)
    ax.set_title(f"sub {c}  (n={sizes[c]:,}, partial {100*(trop.status[labels == c] == 'partial').mean():.0f}%)",
                 fontsize=8)
for j in range(K, nrow * NCOL):
    axes[j // NCOL][j % NCOL].axis("off")
fig.suptitle(f"Eastward sub-clusters k={K} (orange = centroid, blue = member tracks after crossing)", y=1.0)
fig.tight_layout(); plt.show()
"""),
md(r"""
## All sub-clusters on one map
"""),
code(r"""
fig, ax = plt.subplots(figsize=(9, 7))
draw_coast(ax); draw_refs(ax); draw_gate(ax)
allcmap = plt.get_cmap("tab20", K)
for c in range(K):
    lo, la = centroid_track(c)
    ax.plot(lo, la, "-", color=allcmap(c), lw=1.4, alpha=.85, zorder=2)
    ax.text(lo[-1], la[-1], str(c), fontsize=8, ha="center", va="center", zorder=4)
ax.set_title(f"All {K} eastward sub-cluster centroids (crossing -> {C.RADII_KM[-1]} km)")
fig.tight_layout(); plt.show()
"""),
md(r"""
## Assign each sub-cluster a group letter
`ASSIGN[cluster] = "letter"`; same letter => merged. Starts all separate.
"""),
code(r"""
import string
def lbl(c):
    return string.ascii_uppercase[c] if c < 26 else f"g{c}"
ASSIGN = {c: lbl(c) for c in range(K)}

# --- merge by hand, e.g.: ---
# for c in [0, 3]:  ASSIGN[c] = "A"

ASSIGN
"""),
md(r"""
## Preview the merged groups
"""),
code(r"""
letters = sorted(set(ASSIGN.values()))
NCOLg = min(4, len(letters))
nrowg = int(np.ceil(len(letters) / NCOLg))
cmap  = plt.get_cmap("tab20", K)
fig, axes = plt.subplots(nrowg, NCOLg, figsize=(3.4 * NCOLg, 2.7 * nrowg),
                         squeeze=False, sharex=True, sharey=True)
for i, L in enumerate(letters):
    ax = axes[i // NCOLg][i % NCOLg]
    draw_coast(ax); draw_gate(ax)
    mem = [c for c in range(K) if ASSIGN[c] == L]
    for c in mem:
        lo, la = centroid_track(c)
        ax.plot(lo, la, "-", color=cmap(c), lw=1.6)
        ax.plot(lo[-1], la[-1], "o", color=cmap(c), mec="k", ms=5)
    ax.set_title(f"group {L}  ({len(mem)} sub-clusters)", fontsize=9)
for j in range(len(letters), nrowg * NCOLg):
    axes[j // NCOLg][j % NCOLg].axis("off")
fig.suptitle("Merged eastward groups (centroids)", y=1.0)
fig.tight_layout(); plt.show()
"""),
md(r"""
## Export
Prints the grouping; with `SAVE_MODEL = True` also writes one row per subset
particle (`store` / `row` / `traj`, sub-cluster, group) to
`data/tropical_1.6_labels_k<K>.parquet`.
"""),
code(r"""
name2id     = {L: i for i, L in enumerate(letters)}
SUB_MAP     = {c: name2id[ASSIGN[c]] for c in range(K)}
SUB_NAMES   = {i: L for L, i in name2id.items()}

print(f"# gate: direction at {GATE_R} km in {BEARING_RANGE}, statuses {FIT_STATUS} | weights: {_wr}")
print("SUB_MAP =", SUB_MAP)
print("SUB_NAMES =", SUB_NAMES)
print()
for L in letters:
    mem = [c for c in range(K) if ASSIGN[c] == L]
    print(f"  {L}: {mem}  (n={sum(sizes[c] for c in mem):,})")

if SAVE_MODEL:
    out = trop[["trajectory_id", "store", "row", "traj", "status", "bearing"]].assign(
        sub_label=labels.astype(np.int32))
    out["sub_group"] = out.sub_label.map(SUB_MAP).astype(np.int32)
    out["sub_name"] = out.sub_group.map(SUB_NAMES)
    OUT = C.DATA_DIR / f"tropical_1.6_labels_k{K}.parquet"
    out.to_parquet(OUT, index=False)
    print("\nsaved", out.shape, "->", OUT)
"""),
])

# =========================================================================== #
# 03 - assign labels
# =========================================================================== #
save("03_assign_labels.ipynb", [
md(r"""
# 03 - Assign cluster labels to ALL particles  (Stage 3)

Loads the model saved by notebook 1.5 (`data/kmeans_models/manual_1.5_k<K>/`)
with its own scaler, and labels every `complete` and `partial` particle by
nearest centroid. `no_gate` / `no_cross` get `cluster_label = -1`. With
`config.GROUP_MAP` set, `cluster_group` holds the merged groups.

**Output:** `data/labeled_trajectories.parquet` - one row per particle, with
`store` / `row` / `traj` to find the real particle in its Zarr store.
"""),
code(BOOT),
params_code(r"""
BEST_K = 70          # the K saved by notebook 1.5 (papermill: -p BEST_K <k>)
"""),
code(r"""
import joblib
MODEL_DIR = C.manual_model_dir(BEST_K)
km     = joblib.load(MODEL_DIR / f"kmeans_k{BEST_K}.pkl")
scaler = joblib.load(MODEL_DIR / "scaler.pkl")
print("loaded", MODEL_DIR.name, "with", km.n_clusters, "clusters")

W = P.feature_weight_vector()
assert np.allclose(np.load(MODEL_DIR / "weights_W.npy"), W), (
    "config.RADIUS_WEIGHTS does not match the weights this model was fit with "
    "(paste the RADIUS_WEIGHTS printed by notebook 1.5 into config.py)")
print("config.RADIUS_WEIGHTS matches the fit:", C.RADIUS_WEIGHTS)
"""),
md(r"""
## 3.1  Predict
"""),
code(r"""
features = pd.read_parquet(C.FEATURES_FILE)
labelable = features.status.isin(["complete", "partial"]).to_numpy()
X_all = scaler.transform(P.build_feature_matrix(features[labelable])) * W
labels = np.full(len(features), -1, dtype=np.int32)
labels[labelable] = km.predict(X_all).astype(np.int32)
features["cluster_label"] = labels
print(features.cluster_label.value_counts().sort_index().to_string())
"""),
md(r"""
## 3.2  Merge into groups (optional)
"""),
code(r"""
if C.GROUP_MAP:
    groups, raw2grp = P.apply_group_map(features.cluster_label.to_numpy(), C.GROUP_MAP, BEST_K)
    features["cluster_group"] = groups.astype(np.int32)
    print("raw cluster -> group:", raw2grp)
    print(features.loc[features.cluster_group >= 0, "cluster_group"]
          .map(lambda g: C.GROUP_NAMES.get(g, g)).value_counts().to_string())
else:
    features["cluster_group"] = features["cluster_label"]
    print("GROUP_MAP empty -> cluster_group mirrors cluster_label")
"""),
md(r"""
## 3.3  Save
"""),
code(r"""
features.to_parquet(C.LABELED_FILE, index=False)
lbl = features.cluster_label >= 0
print(f"labelled {lbl.sum():,} particles into {BEST_K} clusters; "
      f"{(~lbl).sum():,} unlabelled ({features.loc[~lbl, 'status'].value_counts().to_dict()})")
print("saved", features.shape, "->", C.LABELED_FILE)
"""),
])

# =========================================================================== #
# 04 - diagnostics
# =========================================================================== #
save("04_diagnostics.ipynb", [
md(r"""
# 04 - Diagnostics and figures  (Stage 4)

Pathway maps, where each group is at each radius, how long each group takes to
get there, seasonal / interannual fractions, centroids, and the most typical
particles per label.

`LABEL_COL = "cluster_group"` for the merged groups (needs `config.GROUP_MAP`)
or `"cluster_label"` for the raw clusters.
"""),
code(BOOT + r"""
import joblib
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs, cartopy.feature as cfeature
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap
"""),
params_code(r"""
BEST_K = 70                    # must match notebook 03 (papermill: -p BEST_K <k>)
LABEL_COL = "cluster_group"    # "cluster_group" (merged) or "cluster_label" (raw)
"""),
code(r"""
lab = pd.read_parquet(C.LABELED_FILE)
MODEL_DIR = C.manual_model_dir(BEST_K)
km     = joblib.load(MODEL_DIR / f"kmeans_k{BEST_K}.pkl")
scaler = joblib.load(MODEL_DIR / "scaler.pkl")
W = P.feature_weight_vector()

labelled = lab[lab[LABEL_COL] >= 0].copy()
n_lab = int(labelled[LABEL_COL].max()) + 1
cmap = plt.get_cmap("tab20", max(n_lab, 3))
LABEL_NAMES = C.GROUP_NAMES if LABEL_COL == "cluster_group" else {}

def label_name(c):
    return LABEL_NAMES.get(c, str(c))

# centroids in degrees; group centroid = size-weighted mean in the fitted space
if LABEL_COL == "cluster_group" and C.GROUP_MAP:
    _, raw2grp = P.apply_group_map(np.arange(BEST_K), C.GROUP_MAP, BEST_K)
    sizes = lab.loc[lab.cluster_label >= 0, "cluster_label"].value_counts()
    centers = np.zeros((n_lab, km.cluster_centers_.shape[1])); wsum = np.zeros(n_lab)
    for c in range(BEST_K):
        g, w = raw2grp[c], float(sizes.get(c, 0))
        centers[g] += km.cluster_centers_[c] * w; wsum[g] += w
    centers /= np.where(wsum[:, None] == 0, 1, wsum[:, None])
else:
    centers = km.cluster_centers_[:n_lab]
disp_cent = P.centroids_to_degrees(centers / W, scaler)
start_lon = labelled.groupby(LABEL_COL).cross_lon.mean().reindex(range(n_lab)).to_numpy()

pc = ccrs.PlateCarree()
EXT = [C.DOMAIN["lon_min"], C.DOMAIN["lon_max"], C.DOMAIN["lat_min"], C.DOMAIN["lat_max"]]
def geo_axes_grid(n, w=4.2, h=3.4, ncol=4):
    ncol = min(n, ncol); nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(w * ncol, h * nrow),
                             subplot_kw={"projection": pc}, squeeze=False)
    axf = axes.ravel()
    for a in axf[n:]:
        a.axis("off")
    for a in axf[:n]:
        a.set_extent(EXT, crs=pc)
    return fig, axf
def land(ax):
    ax.add_feature(cfeature.LAND, facecolor="0.85", zorder=2); ax.coastlines(lw=.5, zorder=3)
print(f"labelled particles: {len(labelled):,} | {LABEL_COL}: {n_lab} labels")
"""),
md(r"""
## Figure 1 - Pathway footprint

Up to `C.PLOT_SAMPLE_PER_LABEL` particles per label are read from the Zarr
stores (by `store` / `row`, checked against `traj`). With `FROM_CROSSING =
True` only the part after the 2.5N crossing is binned - the part the clustering
saw; `False` bins the whole track from release (obs 0 skipped).
"""),
code(r"""
FROM_CROSSING = True
N_IO_THREADS  = int(os.environ.get("SLURM_CPUS_PER_TASK", 16))

n_plot = C.PLOT_SAMPLE_PER_LABEL
pick = (labelled.groupby(LABEL_COL, group_keys=False)
        .apply(lambda d: d.sample(min(n_plot, len(d)), random_state=C.RANDOM_STATE)))
pick = pick[["trajectory_id", "store", "row", "traj", "cross_obs", LABEL_COL]] \
           .rename(columns={LABEL_COL: "lab"})
paths = P.read_paths(pick, n_jobs=N_IO_THREADS)
print(f"read {len(paths):,} trajectories from {pick.store.nunique()} stores")

lon_bins = np.linspace(C.DOMAIN["lon_min"], C.DOMAIN["lon_max"], 100 * 4)
lat_bins = np.linspace(C.DOMAIN["lat_min"], C.DOMAIN["lat_max"], 35 * 4)
xs = {c: [] for c in range(n_lab)}; ys = {c: [] for c in range(n_lab)}
for tid, c, k0 in zip(pick.trajectory_id, pick.lab, pick.cross_obs):
    lo, la = paths[int(tid)]
    s = k0 if FROM_CROSSING else 1
    xs[c].append(lo[s:]); ys[c].append(la[s:])
Hlab = np.zeros((n_lab, lat_bins.size - 1, lon_bins.size - 1))
for c in range(n_lab):
    if not xs[c]:
        continue
    x = np.concatenate(xs[c]); y = np.concatenate(ys[c])
    m = ~(np.isnan(x) | np.isnan(y))
    Hlab[c] = np.histogram2d(x[m], y[m], bins=[lon_bins, lat_bins])[0].T

fig = plt.figure(figsize=(11, 7))
ax = plt.axes(projection=pc); ax.set_extent(EXT, crs=pc)
for c in range(n_lab):
    ax.pcolormesh(lon_bins, lat_bins, np.where(Hlab[c] > 0, 1.0, np.nan),
                  cmap=ListedColormap([cmap(c)]), vmin=0, vmax=1, alpha=.5,
                  transform=pc, zorder=1)
land(ax)
ax.legend(handles=[Line2D([0], [0], marker="s", ls="", mec="none", alpha=.5, mfc=cmap(c),
                          label=f"{label_name(c)} (n={int((pick.lab == c).sum())})")
                   for c in range(n_lab)],
          title=LABEL_COL, fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1))
ax.set_title(f"Pathways by {LABEL_COL} (k={BEST_K}, {n_lab} labels)"
             + (" - after crossing 2.5N" if FROM_CROSSING else ""))
fig.savefig(C.FIG_DIR / f"pathway_map_k{BEST_K}_{LABEL_COL}.png", dpi=140, bbox_inches="tight")
plt.show()
"""),
md(r"""
## Figure 1b - one panel per label
"""),
code(r"""
fig, axf = geo_axes_grid(n_lab)
for c in range(n_lab):
    ax = axf[c]
    ax.pcolormesh(lon_bins, lat_bins, np.where(Hlab[c] > 0, 1.0, np.nan),
                  cmap=ListedColormap([cmap(c)]), vmin=0, vmax=1, alpha=.6,
                  transform=pc, zorder=1)
    land(ax)
    ax.set_title(f"{label_name(c)} (n={int((pick.lab == c).sum())})", fontsize=9,
                 color=cmap(c), fontweight="bold")
fig.suptitle(f"Pathways per {LABEL_COL} (k={BEST_K})", y=1.0, fontsize=12)
fig.tight_layout()
fig.savefig(C.FIG_DIR / f"pathway_maps_by_{LABEL_COL}_k{BEST_K}.png", dpi=130, bbox_inches="tight")
plt.show()
"""),
md(r"""
## Figure 1c - where each group exits one circle, and timing per radius

The footprint integrates the whole track. The first figure freezes one radius
(`SNAP_R`): where each group's particles leave that circle. The second shows,
per group, the median days after crossing to reach each radius (25-75% band) -
the timing the clustering itself ignores.
"""),
code(r"""
SNAP_R = C.RADII_KM[2]          # any radius in C.RADII_KM

la_c, lo_c = P.lat_col(SNAP_R), P.lon_col(SNAP_R)
snap = labelled[[LABEL_COL, la_c, lo_c]].dropna()
fig, axf = geo_axes_grid(n_lab, h=2.6)
for c in range(n_lab):
    s = snap[snap[LABEL_COL] == c]
    h = np.histogram2d(s[lo_c], s[la_c], bins=[lon_bins, lat_bins])[0]
    axf[c].pcolormesh(lon_bins, lat_bins, np.where(h.T > 0, 1.0, np.nan),
                      cmap=ListedColormap([cmap(c)]), vmin=0, vmax=1, alpha=.7,
                      transform=pc, zorder=1)
    land(axf[c])
    axf[c].set_title(f"{label_name(c)}  (n={len(s):,})", fontsize=9, color=cmap(c),
                     fontweight="bold")
fig.suptitle(f"Where each group leaves the {SNAP_R} km circle (k={BEST_K})", y=1.0)
fig.tight_layout(); plt.show()

fig, ax = plt.subplots(figsize=(9, 5.5))
for c in range(n_lab):
    s = labelled[labelled[LABEL_COL] == c]
    q = np.array([s[P.days_col(r)].quantile([.25, .5, .75]).to_numpy() for r in C.RADII_KM])
    ax.fill_between(C.RADII_KM, q[:, 0], q[:, 2], color=cmap(c), alpha=.12, lw=0)
    ax.plot(C.RADII_KM, q[:, 1], "-o", color=cmap(c), lw=1.8, ms=4, label=label_name(c))
ax.set_xlabel("radius around the crossing point [km]")
ax.set_ylabel("days after crossing to get there")
ax.set_xticks(C.RADII_KM); ax.grid(axis="y", color="0.9", lw=.6)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.legend(fontsize=8, ncol=2, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
ax.set_title("Time to reach each radius per group (median, 25-75%; particles that "
             "got there)", fontsize=10, loc="left")
fig.tight_layout(); plt.show()
"""),
md(r"""
## Figure 2 - Seasonal fractions (by crossing month and by release month)
"""),
code(r"""
def fraction_table(group_col):
    g = labelled.groupby([group_col, LABEL_COL]).size().unstack(fill_value=0)
    return g.div(g.sum(axis=1), axis=0) * 100

fig, axes = plt.subplots(1, 2, figsize=(16, 5), sharey=True)
for ax, col in zip(axes, ["cross_month", "release_month"]):
    seas = fraction_table(col).reindex(range(1, 13)).fillna(0)
    bottom = np.zeros(12)
    for c in range(n_lab):
        v = seas.get(c, pd.Series(0, index=seas.index)).to_numpy()
        ax.bar(seas.index, v, bottom=bottom, color=cmap(c), label=label_name(c))
        bottom += v
    ax.set_xlabel(col.replace("_", " ")); ax.set_xticks(range(1, 13))
axes[0].set_ylabel("% of particles")
axes[1].legend(ncol=2, fontsize=7, bbox_to_anchor=(1.01, 1), loc="upper left")
fig.suptitle(f"Seasonal fractions ({LABEL_COL})")
fig.tight_layout()
fig.savefig(C.FIG_DIR / f"seasonal_fractions_k{BEST_K}_{LABEL_COL}.png", dpi=130, bbox_inches="tight")
plt.show()
"""),
md(r"""
## Figure 3 - Interannual fractions (by crossing year)
"""),
code(r"""
yr = fraction_table("cross_year").sort_index()
fig, ax = plt.subplots(figsize=(11, 5))
ax.stackplot(yr.index, *[yr.get(c, pd.Series(0, index=yr.index)).to_numpy() for c in range(n_lab)],
             colors=[cmap(c) for c in range(n_lab)], labels=[label_name(c) for c in range(n_lab)])
ax.set_xlabel("crossing year"); ax.set_ylabel("% of particles"); ax.set_ylim(0, 100)
ax.set_title(f"Interannual fractions ({LABEL_COL})")
ax.legend(ncol=2, fontsize=7, bbox_to_anchor=(1.01, 1), loc="upper left")
fig.savefig(C.FIG_DIR / f"interannual_fractions_k{BEST_K}_{LABEL_COL}.png", dpi=130, bbox_inches="tight")
plt.show()
"""),
md(r"""
## Figure 4 - Days to reach `TRANSIT_R` per label
From `days_<R>km` in the features file (no Zarr reading).
"""),
code(r"""
TRANSIT_R = C.RADII_KM[2]
col = P.days_col(TRANSIT_R)
ncol = 5; nrow = int(np.ceil(n_lab / ncol))
fig, axes = plt.subplots(nrow, ncol, figsize=(3 * ncol, 2.4 * nrow), squeeze=False)
for c in range(n_lab):
    ax = axes[c // ncol][c % ncol]
    d = labelled.loc[labelled[LABEL_COL] == c, col].dropna()
    ax.hist(d, bins=40, color=cmap(c))
    ax.set_title(f"{label_name(c)} (median {d.median():.0f} d)", fontsize=8)
    ax.set_xlabel(f"days crossing -> {TRANSIT_R} km", fontsize=7)
for j in range(n_lab, nrow * ncol):
    axes[j // ncol][j % ncol].axis("off")
fig.tight_layout()
fig.savefig(C.FIG_DIR / f"transit_{TRANSIT_R}km_k{BEST_K}_{LABEL_COL}.png", dpi=120)
plt.show()
"""),
md(r"""
## Figure 5 - Centroids (mean crossing point -> exit at each radius)
"""),
code(r"""
pct = labelled[LABEL_COL].value_counts(normalize=True).sort_index() * 100
markers = ["o", "s", "*", "^", "D", "P"]
fig = plt.figure(figsize=(11, 7))
ax = plt.axes(projection=pc); ax.set_extent(EXT, crs=pc); land(ax)
ax.axhline(C.LAT_CROSS, color="k", lw=.6, ls="--")
for c in range(n_lab):
    lats = disp_cent[c, 0::2]; lons = disp_cent[c, 1::2]
    ax.plot(np.r_[start_lon[c], lons], np.r_[C.LAT_CROSS, lats], "-", color=cmap(c),
            lw=1, alpha=.6, transform=pc)
    for j in range(len(C.RADII_KM)):
        ax.scatter(lons[j], lats[j], color=cmap(c), s=90, marker=markers[j % len(markers)],
                   edgecolor="k", transform=pc, zorder=4)
    ax.text(lons[-1], lats[-1], f" {label_name(c)} ({pct.get(c, 0):.0f}%)", fontsize=8, transform=pc)
ax.legend(handles=[Line2D([0], [0], marker=markers[j % len(markers)], color="k", ls="",
                          mfc="0.7", label=f"{r} km") for j, r in enumerate(C.RADII_KM)],
          loc="lower right", fontsize=8)
ax.set_title(f"Centroids ({LABEL_COL}, k={BEST_K})")
fig.savefig(C.FIG_DIR / f"centroids_k{BEST_K}_{LABEL_COL}.png", dpi=140, bbox_inches="tight")
plt.show()
"""),
md(r"""
## Table 1 - Summary per label
"""),
code(r"""
month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
R_last = C.RADII_KM[-1]
rows = []
for c in range(n_lab):
    s = labelled[labelled[LABEL_COL] == c]
    row = dict(label=c, name=label_name(c), pct=round(100 * len(s) / len(labelled), 1),
               pct_partial=round(100 * (s.status == "partial").mean(), 1),
               peak_cross_month=month_names[int(s.cross_month.mode().iloc[0]) - 1],
               median_days_to_cross=round(float(s.days_to_cross.median()), 1))
    for r in C.RADII_KM:
        row[f"median_{P.days_col(r)}"] = round(float(s[P.days_col(r)].median()), 1)
    row[f"mean_lat_{R_last}km"] = round(float(s[P.lat_col(R_last)].mean()), 2)
    row[f"mean_lon_{R_last}km"] = round(float(s[P.lon_col(R_last)].mean()), 2)
    rows.append(row)
summary = pd.DataFrame(rows)
summary.to_csv(C.DATA_DIR / f"pathway_summary_k{BEST_K}_{LABEL_COL}.csv", index=False)
print(summary.to_string(index=False))
"""),
md(r"""
## Table 2 - Top-20 representative particles per label

The `N_REP` particles closest to their label's centroid in the space k-means
was fit in (standardized, weighted). Each row has `store` / `row` / `traj`, so
the real particle can be opened directly.
"""),
code(r"""
N_REP = 20
Xw = scaler.transform(P.build_feature_matrix(labelled)) * W
diff = Xw - centers[labelled[LABEL_COL].to_numpy()]
labelled["dist_to_centroid"] = np.sqrt(np.einsum("ij,ij->i", diff, diff))

id_cols = [c for c in ("trajectory_id", "store", "row", "traj", "cluster_label",
                       "cluster_group", "status", "cross_time", "days_to_cross")
           if c in labelled.columns and c != LABEL_COL]
reps = (labelled.sort_values("dist_to_centroid").groupby(LABEL_COL, group_keys=False)
        .head(N_REP).sort_values([LABEL_COL, "dist_to_centroid"]).copy())
reps["name"] = reps[LABEL_COL].map(label_name)
reps["rank"] = reps.groupby(LABEL_COL).cumcount() + 1
reps = reps[[LABEL_COL, "name", "rank", "dist_to_centroid", *id_cols, *P.feature_columns()]]
out_csv = C.DATA_DIR / f"top{N_REP}_representatives_k{BEST_K}_{LABEL_COL}.csv"
reps.to_csv(out_csv, index=False)
print(f"wrote {len(reps):,} rows -> {out_csv}")
reps.head(N_REP)
"""),
code(r"""
rep_pick = reps[["trajectory_id", "store", "row", "traj", LABEL_COL]] \
               .rename(columns={LABEL_COL: "lab"})
rep_pick = rep_pick.merge(labelled[["trajectory_id", "cross_obs"]], on="trajectory_id")
rep_paths = P.read_paths(rep_pick, n_jobs=N_IO_THREADS)

fig, axf = geo_axes_grid(n_lab)
for c in range(n_lab):
    ax = axf[c]
    for tid, k0 in rep_pick.loc[rep_pick.lab == c, ["trajectory_id", "cross_obs"]].itertuples(index=False):
        lo, la = rep_paths[int(tid)]
        m = ~(np.isnan(lo) | np.isnan(la)); m[:k0] = False      # after crossing only
        ax.plot(lo[m], la[m], "-", color=cmap(c), lw=.8, alpha=.7, transform=pc)
    ax.plot(np.r_[start_lon[c], disp_cent[c, 1::2]], np.r_[C.LAT_CROSS, disp_cent[c, 0::2]],
            "-o", color="k", lw=1.4, ms=2, zorder=5, transform=pc)
    land(ax)
    ax.set_title(f"{label_name(c)} (top {N_REP})", fontsize=9, color=cmap(c), fontweight="bold")
fig.suptitle(f"Top-{N_REP} representative particles per {LABEL_COL} (k={BEST_K}), "
             f"after crossing; black = centroid", y=1.0, fontsize=12)
fig.tight_layout()
fig.savefig(C.FIG_DIR / f"top{N_REP}_representatives_k{BEST_K}_{LABEL_COL}.png",
            dpi=130, bbox_inches="tight")
plt.show()
"""),
md(r"""
## Figure 6 - Animated: where each group leaves each circle
One frame per radius in `C.RADII_KM`.
"""),
code(r"""
import matplotlib.animation as animation
from IPython.display import Image, display

GIF_FPS  = 1.2
GIF_NAME = C.FIG_DIR / f"radius_snapshots_k{BEST_K}_{LABEL_COL}.gif"

occ = {}
for r in C.RADII_KM:
    for c in range(n_lab):
        s = labelled.loc[labelled[LABEL_COL] == c, [P.lat_col(r), P.lon_col(r)]].dropna()
        h = np.histogram2d(s[P.lon_col(r)], s[P.lat_col(r)], bins=[lon_bins, lat_bins])[0]
        occ[(c, r)] = np.where(h.T > 0, 1.0, np.nan)

fig, axf = geo_axes_grid(n_lab, h=2.6)
meshes = []
for c in range(n_lab):
    land(axf[c])
    meshes.append(axf[c].pcolormesh(lon_bins, lat_bins, occ[(c, C.RADII_KM[0])],
                                    cmap=ListedColormap([cmap(c)]), vmin=0, vmax=1,
                                    alpha=.7, transform=pc, zorder=1))
    axf[c].set_title(label_name(c), fontsize=9, color=cmap(c), fontweight="bold")
sup = fig.suptitle("", y=1.0, fontsize=13)
fig.tight_layout()

def _frame(i):
    r = C.RADII_KM[i]
    for c in range(n_lab):
        meshes[c].set_array(occ[(c, r)].ravel())
    sup.set_text(f"Where each group leaves the {r} km circle (k={BEST_K})")
    return meshes + [sup]

anim = animation.FuncAnimation(fig, _frame, frames=len(C.RADII_KM), blit=False)
anim.save(GIF_NAME, writer=animation.PillowWriter(fps=GIF_FPS), dpi=90)
plt.close(fig)
display(Image(filename=GIF_NAME))
"""),
])
