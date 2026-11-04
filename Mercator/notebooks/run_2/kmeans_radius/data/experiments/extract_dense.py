"""Dense-radius features on every 5th store, for the radius/weight experiments.
Same extraction as notebook 01 (pipeline.extract_store_features), only with
more radii. Output: data/experiments/features_dense.parquet."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import numpy as np, pandas as pd
import config as C
R_DENSE = [50, 100, 150, 200, 300, 400, 500, 750, 1000, 1250, 1500, 1750, 2000]
C.RADII_KM = R_DENSE                      # extract_store_features reads C.RADII_KM
import pipeline as P
from joblib import Parallel, delayed
OUT = C.DATA_DIR / "experiments"
stores = []
for d in C.TRACK_DIRS:
    stores += sorted((C.DATA_ROOT / d).glob(C.STORE_GLOB))[::5]
def one(s):
    import config as C2; C2.RADII_KM = R_DENSE
    part = OUT / "parts" / f"{s.stem}.parquet"
    if not part.exists():
        P.extract_store_features(s).to_parquet(part, index=False)
Parallel(n_jobs=32, backend="loky")(delayed(one)(s) for s in stores)
f = pd.concat((pd.read_parquet(OUT / "parts" / f"{s.stem}.parquet") for s in stores), ignore_index=True)
f["store"] = f["store"].astype("category")
f.to_parquet(OUT / "features_dense.parquet", index=False)
print(len(stores), "stores,", f"{len(f):,} particles ->", OUT / "features_dense.parquet")
print(f.status.value_counts(normalize=True).round(4).to_dict())
