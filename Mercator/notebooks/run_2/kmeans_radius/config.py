"""Central configuration for the run_2 RADIUS k-means pipeline.

Variant of `run_2/kmeans` (which sampled positions at fixed DAYS after release).
Here the clock starts when each particle first crosses `LAT_CROSS` (2.5N), and
the features are WHERE the particle first gets farther than each radius in
`RADII_KM` from its OWN crossing point (haversine distance):

    X_i = [lat_200km, lon_200km, lat_500km, lon_500km, ..., lat_2000km, lon_2000km]

Every column is standardized to mean 0 / std 1 (StandardScaler) and each radius
is then re-weighted by `RADIUS_WEIGHTS`, exactly like the day-based pipeline.
Notebook 00 shows why these radii were chosen.

Edit paths and parameters here; every notebook imports this module.
"""
from pathlib import Path

# --------------------------------------------------------------------------- #
# Input data: run_2 Parcels Zarr stores (~10,100 trajectories each).
# --------------------------------------------------------------------------- #
DATA_ROOT = Path("/work/bk1450/b383184/Amazon/Mercator/data/run_2")
TRACK_DIRS = ["tracks_v3_11098723", "tracks_v3_45678",
              "tracks_v3_67891", "tracks_v3_78876"]
STORE_GLOB = "Parcels_run_*.zarr"


def list_stores():
    """Full, sorted list of input Zarr stores across all track dirs."""
    stores = []
    for d in TRACK_DIRS:
        stores += sorted((DATA_ROOT / d).glob(STORE_GLOB))
    return stores


def store_paths_by_name():
    """{store name (path stem) -> path}.  Stores are always looked up by NAME,
    never by their position in `list_stores()` (that shifts when a store is
    added or removed)."""
    return {p.stem: p for p in list_stores()}


# --------------------------------------------------------------------------- #
# Output locations (this project).
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
FEATURE_PARTS_DIR = DATA_DIR / "features_parts"   # one parquet per store
FEATURES_FILE = DATA_DIR / "features.parquet"     # Stage 1 combined output
MODELS_DIR = DATA_DIR / "kmeans_models"           # Stage 2 / 1.5 pickles
LABELED_FILE = DATA_DIR / "labeled_trajectories.parquet"  # Stage 3 output
FIG_DIR = PROJECT_ROOT / "figures"

for _p in (DATA_DIR, FEATURE_PARTS_DIR, MODELS_DIR, FIG_DIR):
    _p.mkdir(parents=True, exist_ok=True)


def manual_model_dir(k):
    """Where notebook 1.5 saves its fit for K=k (read by notebooks 03 / 04)."""
    return MODELS_DIR / f"manual_1.5_k{k}"


# --------------------------------------------------------------------------- #
# Feature-extraction parameters (Stage 1).
# --------------------------------------------------------------------------- #
# Starting line: the first 6-hourly output where a particle goes from south of
# LAT_CROSS to at/north of it (same rule as
# analysis/particle_diagnostics/Regroup_particles.ipynb).  No run_2 particle is
# released north of 2.5N, so this is always the first northward crossing.
LAT_CROSS = 2.5

# Radii (km) around each particle's own crossing point.  The feature for radius
# R is the position at the first output farther than R from the crossing point.
# The first entry is the GATE: a particle that crosses but never gets this far
# is `no_gate` (not clustered).  See notebook 00 for the choice.
RADII_KM = [200, 500, 1000, 1500, 2000]

EARTH_RADIUS_KM = 6371.0

# --------------------------------------------------------------------------- #
# Clustering parameters (Stage 2 / 1.5 / 3).
# --------------------------------------------------------------------------- #
N_SUB = 500_000
K_LIST = [50, 70, 100, 200]
RANDOM_STATE = 42
SILHOUETTE_SAMPLE = 50_000

# Per-radius weighting applied AFTER z-standardization.  Each radius' two
# columns (lat, lon) are multiplied by sqrt(w), so that radius' contribution to
# the k-means squared distance is scaled by exactly w.  All 1.0 = every radius
# counts the same.  Notebook 1.5 tunes its own copy; once you are happy, paste
# the weights here so notebooks 03 / 04 use the same ones (03 checks this).
# Keys MUST cover every radius in RADII_KM.
RADIUS_WEIGHTS = {200: 0.03, 500: 0.17, 1000: 0.66, 1500: 1.5, 2000: 2.65}

# --------------------------------------------------------------------------- #
# Map domain (figures).
# --------------------------------------------------------------------------- #
DOMAIN = dict(lon_min=-95, lon_max=5, lat_min=-8, lat_max=29)

# How many full trajectories to read PER LABEL for the pathway maps
# (notebook 04).  Bounds the Zarr I/O; not the k-means subsample (N_SUB).
PLOT_SAMPLE_PER_LABEL = 5000

# --------------------------------------------------------------------------- #
# Manual cluster grouping ("over-resolve, then merge").
#
# Fill these from the export cell of notebook 1.5.  Map each raw k-means cluster
# id -> group id; clusters left out stay their own group.  Empty = no merging.
# The old day-based map does NOT carry over: these are new clusters.
# --------------------------------------------------------------------------- #
GROUP_MAP = {}
GROUP_NAMES = {}
