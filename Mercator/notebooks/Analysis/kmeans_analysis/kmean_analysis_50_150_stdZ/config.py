"""Central configuration for the Amazon plume k-means trajectory clustering pipeline.

This is the **50 / 100 / 150-day, z-standardized** variant.  Instead of embedding
positions on the unit sphere (the xyz / haversine trick used by the sibling
projects), each raw feature (lat_50, lon_50, lat_100, lon_100, lat_150, lon_150)
is standardized to mean 0, std 1 BEFORE k-means.  Standardization gives every day
EQUAL statistical weight: without it, particles disperse over time so the later
day (which has the largest spatial variance) dominates the Euclidean distance and
k-means effectively weights the last day the most.  On top of that equal-weight
baseline, DAY_WEIGHTS (below) optionally re-weights each day on purpose (e.g. give
the final position more say).  See README.

Edit paths and parameters here; every notebook imports from this module so there
is a single source of truth.
"""
from pathlib import Path

# --------------------------------------------------------------------------- #
# Input data: Parcels OceanParcels Zarr stores (10,000 trajectories each).
# --------------------------------------------------------------------------- #
DATA_ROOT = Path("/work/bk1450/b383184/Amazon/Mercator/data")
TRACK_DIRS = ["tracks_45678", "tracks_67891", "tracks_78876"]
STORE_GLOB = "Parcels_run_*_*.zarr"


def list_stores():
    """Return the full, sorted list of input Zarr stores across all track dirs."""
    stores = []
    for d in TRACK_DIRS:
        stores += sorted((DATA_ROOT / d).glob(STORE_GLOB))
    return stores


# --------------------------------------------------------------------------- #
# Output locations (this project).
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
FEATURE_PARTS_DIR = DATA_DIR / "features_parts"   # one parquet per store
FEATURES_FILE = DATA_DIR / "features.parquet"     # Stage 1 combined output
MODELS_DIR = DATA_DIR / "kmeans_models"           # Stage 2 pickles
LABELED_FILE = DATA_DIR / "labeled_trajectories.parquet"  # Stage 3 output
FIG_DIR = PROJECT_ROOT / "figures"

for _p in (DATA_DIR, FEATURE_PARTS_DIR, MODELS_DIR, FIG_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# Feature-extraction parameters (Stage 1).
# --------------------------------------------------------------------------- #
# Position sampling times: days after each particle's own release.  This variant
# uses THREE snapshots (50, 100, 150 days).  The first entry is the "gate" day: a
# trajectory that never reaches it is `early_loss` (unusable); trajectories that
# reach the gate but not every later day are `partial` (last-known position used
# as the proxy for the missing later day(s)).
DAYS = [30, 50, 100, 150]

# A target time is considered "reached" only if a valid observation exists
# within this tolerance (days) of t_release + N days.  Output is 6-hourly,
# so 1 day is a generous window that still rejects truncated / deleted tracks.
TIME_TOL_DAYS = 1.0

# Each store holds this many trajectories; used to build globally-unique ids.
TRAJ_PER_STORE = 10000

# --------------------------------------------------------------------------- #
# Clustering parameters (Stage 2 / 3).
# --------------------------------------------------------------------------- #
N_SUB = 200_000
K_LIST = [15, 20, 25, 30, 35, 40, 45, 50, 55]
RANDOM_STATE = 42
SILHOUETTE_SAMPLE = 50_000

# Feature space for k-means:
#   "zscore" -> raw geographic features [lat_50, lon_50, lat_100, lon_100,
#              lat_150, lon_150] standardized to mean 0 / std 1 per column by a
#              StandardScaler fit on the subsample (saved inside the model
#              Pipeline).  Equal weight per day BEFORE the optional DAY_WEIGHTS
#              below; NO spherical projection.  This is the method this project
#              exists to implement.
#   "xyz"    -> legacy: embed each position on the unit sphere as Cartesian
#              (x, y, z) and cluster with plain k-means (haversine-consistent).
#   "cosine" -> legacy: [lat, lon*cos(MEAN_LAT)] in degrees.
FEATURE_SPACE = "zscore"

# Per-day weighting applied AFTER z-standardization (FEATURE_SPACE == "zscore").
# Standardization makes every day's variance 1 (equal weight); DAY_WEIGHTS then
# re-weights each day's contribution to the k-means squared-distance objective.
# A day's two columns (lat, lon) are each multiplied by sqrt(w), so that day's
# squared-distance contribution is scaled by exactly w.  This is the SINGLE
# source of truth: notebooks 02 (fit), 03 (predict) and 04 (centroid degrees)
# all build the multiplier from this dict via pipeline.feature_weight_vector().
# Set every value to 1.0 to recover pure equal-weight standardization.
# Keys MUST cover every day in DAYS.

# DAY_WEIGHTS = {
#     30:  0.5,   # early position, low discriminating power
#     50:  1.0,   # intermediate
#     100: 1.5,   # getting informative
#     150: 2.0,   # most important -- where did the particle end up?
# }

DAY_WEIGHTS = {30: 1.0, 50: 2.0, 100: 1.0, 150: 2.0}
# Reference latitude for the (legacy) longitude cosine correction; only used when
# FEATURE_SPACE == "cosine".  Set MEAN_LAT = None to disable the correction.
MEAN_LAT = 5.0

# --------------------------------------------------------------------------- #
# Map domain (Stage 4 figures).
# --------------------------------------------------------------------------- #
DOMAIN = dict(lon_min=-95, lon_max=5, lat_min=-8, lat_max=27)

# Key locations for transit-time diagnostics (lat, lon).
TRANSIT_TARGETS = {
    "10N": (10.0, None),       # first crossing of 10N
    "38W": (None, -38.0),      # first crossing of 38W
    "61.5W": (None, -61.5),    # first crossing of 61.5W
}

# --------------------------------------------------------------------------- #
# Manual cluster grouping (the "over-resolve then merge" workflow).
#
# Strategy: run k-means at a fairly high BEST_K (e.g. 20-25) so the structure is
# over-resolved into many fine clusters, then merge the fine clusters that
# represent the SAME physical pathway into a handful of named groups here.
#
# Fill GROUP_MAP after inspecting notebook 02 (use the centroid dendrogram there
# as a starting suggestion).  Map each raw k-means cluster id -> a group id.
# Any cluster id you leave out stays in its own singleton group automatically.
# Leave GROUP_MAP empty ({}) to keep the raw clusters ungrouped.
#
# NOTE: the fine-cluster -> group assignment depends on the feature space and the
# number of snapshot days, so any map inherited from the xyz 50/100-day project
# would be meaningless here.  Start empty; re-inspect notebook 02's dendrogram in
# THIS project and build the map before trusting merged groups.
# GROUP_MAP = {}
GROUP_MAP = {0: 1, 1: 5, 2: 4, 3: 1, 4: 2, 5: 3, 6: 1, 7: 0, 8: 1, 9: 5, 10: 3, 11: 1, 12: 3, 13: 1, 14: 5, 15: 1, 16: 5, 17: 0, 18: 4, 19: 3, 20: 2, 21: 1, 22: 1, 23: 4, 24: 1, 25: 5, 26: 5, 27: 5, 28: 1, 29: 1, 30: 3, 31: 0, 32: 1, 33: 0, 34: 1, 35: 4, 36: 1, 37: 2, 38: 5, 39: 0}

# Human-readable names for the groups (group id -> label). Optional.
# GROUP_NAMES = {}
GROUP_NAMES = {
    0: "A",
    1: "B",
    2: "C",
    3: "D",
    4: "E",
    5: "F",
}
