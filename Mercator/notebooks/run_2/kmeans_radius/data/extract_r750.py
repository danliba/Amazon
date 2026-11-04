"""Exit point at 750 km (lat/lon/days) for every particle, in the row order of
data/features.parquet (stores in config.list_stores() order, rows 0..n-1), for
v4.1.5_Manual_clustering. Extracted with radii [200, 750] so the gate is still
200 km: a particle that never gets 750 km away keeps its LAST position as the
stand-in (same rule as the other radii). Output: data/features_r750.parquet."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pandas as pd
import config as C
from joblib import Parallel, delayed

PARTS = C.DATA_DIR / "features_r750_parts"; PARTS.mkdir(exist_ok=True)
COLS = ["store", "row", "traj", "lat_750km", "lon_750km", "days_750km"]

def one(s):
    import config as C2
    C2.RADII_KM = [200, 750]                       # extract_store_features reads C.RADII_KM
    import pipeline as P2
    part = PARTS / f"{s.stem}.parquet"
    if not part.exists():
        P2.extract_store_features(s)[COLS].to_parquet(part, index=False)

stores = C.list_stores()
Parallel(n_jobs=int(os.environ.get("SLURM_CPUS_PER_TASK", 16)), backend="loky")(delayed(one)(s) for s in stores)
r = pd.concat((pd.read_parquet(PARTS / f"{s.stem}.parquet") for s in stores), ignore_index=True)
f = pd.read_parquet(C.FEATURES_FILE, columns=["store", "row", "traj"])
assert len(r) == len(f) and (r.row.to_numpy() == f.row.to_numpy()).all() \
    and (r.traj.to_numpy() == f.traj.to_numpy()).all(), "750 km rows do not line up with features.parquet"
r[["lat_750km", "lon_750km", "days_750km"]].to_parquet(C.DATA_DIR / "features_r750.parquet", index=False)
print(f"{len(r):,} rows -> {C.DATA_DIR / 'features_r750.parquet'}; "
      f"reached 750 km: {100 * r.days_750km.notna().mean():.1f}%")
