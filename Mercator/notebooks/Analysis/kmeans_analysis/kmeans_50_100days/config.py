"""Central configuration for the Amazon plume k-means trajectory clustering pipeline.

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
DAY_INTER = 50      # intermediate position: days after each particle's release
DAY_END = 100       # endpoint position:    days after each particle's release
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
K_LIST = [15, 20, 25, 30, 35]
RANDOM_STATE = 42
SILHOUETTE_SAMPLE = 50_000

# Feature space for k-means:
#   "xyz"    -> embed each position on the unit sphere as Cartesian (x, y, z) and
#              cluster with plain k-means.  Euclidean distance there is the chord,
#              a monotonic function of the great-circle (haversine) distance, so
#              this is *haversine clustering* with proper spherical centroids.
#              Each position -> 3 columns, so the feature vector is 6-D.
#   "cosine" -> legacy: [lat, lon*cos(MEAN_LAT)] in degrees (4-D).  A cheap linear
#              approximation that is only accurate very near the equator.
FEATURE_SPACE = "xyz"

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
# Example for BEST_K = 20:
#   GROUP_MAP = {0:0, 5:0, 9:0,      # group 0: NBC retroflection
#                1:1, 3:1,           # group 1: Caribbean / coastal
#                2:2, 7:2, 8:2}      # group 2: equatorial export   ...etc
# GROUP_MAP = {}
GROUP_MAP = {
    # group 0
    5: 0, 11: 0, 26: 0,
    # group 1
    0: 1, 2: 1, 9: 1, 10: 1, 14: 1, 19: 1, 29: 1,
    # group 2
    12: 2, 16: 2,
    # group 3
    3: 3, 6: 3, 13: 3, 18: 3, 21: 3, 23: 3, 24: 3,
    # group 4
    4: 4, 15: 4, 25: 4,
    # group 5
    1: 5, 7: 5, 8: 5, 17: 5, 20: 5, 22: 5, 27: 5, 28: 5,
}

# Human-readable names for the groups (group id -> label). Optional.
# GROUP_NAMES = {}
GROUP_NAMES = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F"}

