"""Refit the k=50 model of notebook 1.5 and persist it.

Notebook 1.5 fits MiniBatchKMeans in-memory and never saves it, so the manual
ASSIGN grouping is anchored to cluster ids that only existed in a dead kernel.
This script reproduces that fit, VERIFIES it against the fingerprint stored in
the notebook's own cell outputs, and only then writes the artefacts.

Its DAY_WEIGHTS differ from config.DAY_WEIGHTS on purpose: the notebook tunes
them locally, so the model is written under its own name and never touches
data/kmeans_models/kmeans_k50.pkl (that one belongs to notebook 02).
"""
import sys, os, json
sys.path.insert(0, os.path.abspath(".."))
import numpy as np
import pandas as pd
import joblib
from itertools import combinations
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
import config as C
import pipeline as P

# --- verbatim from notebook 1.5, cell 1 --------------------------------------
K = 50
DAY_WEIGHTS = {30: 0.5, 50: 1.5, 100: 1.0, 150: 1.5, 180: 2.0}
_wd = DAY_WEIGHTS if DAY_WEIGHTS is not None else C.DAY_WEIGHTS
W = np.array([np.sqrt(_wd[d]) for d in C.DAYS for _ in range(2)])

# --- verbatim from notebook 1.5, cell 3 --------------------------------------
features = pd.read_parquet(C.FEATURES_FILE)
complete = features[features.status == "complete"]
sub = complete.sample(n=min(C.N_SUB, len(complete)),
                      random_state=C.RANDOM_STATE).reset_index(drop=True)

X_raw = P.build_feature_matrix(sub)
scaler = StandardScaler().fit(X_raw)
X_sub = scaler.transform(X_raw) * W

km = MiniBatchKMeans(n_clusters=K, random_state=C.RANDOM_STATE,
                     batch_size=10000, n_init=10, max_iter=300)
labels = km.fit_predict(X_sub)
sizes = np.bincount(labels, minlength=K)
cent_deg = P.centroids_to_degrees(km.cluster_centers_ / W, scaler)
print(f"fit k={K} on {len(sub):,} trajectories | "
      f"cluster sizes {sizes.min()}..{sizes.max()}")

# --- verify against the fingerprint stored in the notebook -------------------
# The grouping in effect when cell 16 ran (exec 12), transcribed from that
# cell's own output. It is NOT the current cell 13 (exec 19): 9 was S1 and
# 10/34 were B1 back then. Only this version can validate the refit, because
# the printed distances were computed under it.
_MEMBERS_AT_FIT = {
    "A1": [16, 31], "A12": [35], "A2": [0, 5, 20, 22, 36, 39, 42], "A3": [33],
    "B1": [2, 10, 34, 40, 48], "B2": [7, 13, 23, 28, 29, 38, 46], "B3": [11, 24],
    "BS": [3, 17, 43], "C": [6, 12, 30, 44], "CB": [26, 47], "E": [18, 32],
    "E0": [21], "E1": [1, 49], "E2": [4, 27], "F": [8, 14, 45],
    "S": [15, 19, 25, 37, 41], "S1": [9],
}
ASSIGN_AT_FIT = {c: L for L, m in _MEMBERS_AT_FIT.items() for c in m}
assert len(ASSIGN_AT_FIT) == K
EXPECTED_SIZE_RANGE = (1156, 98976)
EXPECTED_WITHIN = {  # group -> max within-group centroid distance, from cell 16
    "A1": 6.5, "A12": 0.0, "A2": 16.0, "A3": 0.0, "B1": 10.8, "B2": 12.9,
    "B3": 8.9, "BS": 12.2, "C": 18.6, "CB": 10.8, "E": 2.7, "E0": 0.0,
    "E1": 2.6, "E2": 1.5, "F": 17.8, "S": 20.9, "S1": 0.0,
}


def cdist(a, b):
    return float(np.sqrt(((cent_deg[a] - cent_deg[b]) ** 2).sum()))


ok = True
got_range = (int(sizes.min()), int(sizes.max()))
if got_range != EXPECTED_SIZE_RANGE:
    ok = False
    print(f"MISMATCH cluster size range: got {got_range}, "
          f"expected {EXPECTED_SIZE_RANGE}")

for L, exp in EXPECTED_WITHIN.items():
    m = [c for c in range(K) if ASSIGN_AT_FIT[c] == L]
    got = max((cdist(a, b) for a, b in combinations(m, 2)), default=0.0)
    if abs(got - exp) > 0.05:
        ok = False
        print(f"MISMATCH group {L}: got {got:.1f} deg, expected {exp:.1f} deg")

# the 12 closest different-label pairs, from cell 16's second block
EXPECTED_PAIRS = [(1.6, 4, 32), (2.9, 1, 27), (3.0, 27, 32), (4.0, 4, 18),
                  (4.0, 1, 4), (4.1, 21, 49), (4.3, 9, 15), (4.6, 10, 28),
                  (5.0, 18, 27), (5.0, 28, 34), (5.3, 6, 47), (5.3, 10, 13)]
for exp, a, b in EXPECTED_PAIRS:
    got = cdist(a, b)
    if abs(got - exp) > 0.05:
        ok = False
        print(f"MISMATCH pair {a}<->{b}: got {got:.1f} deg, expected {exp:.1f} deg")

if not ok:
    print("\nFIT DID NOT REPRODUCE - cluster ids would not match ASSIGN. "
          "Nothing written.")
    sys.exit(1)
print("fingerprint OK - cluster ids match the ones the manual ASSIGN was made on")

# --- persist -----------------------------------------------------------------
outdir = C.MODELS_DIR / "manual_1.5_k50"
outdir.mkdir(parents=True, exist_ok=True)
joblib.dump(km, outdir / "kmeans_k50.pkl")
joblib.dump(scaler, outdir / "scaler.pkl")
np.save(outdir / "weights_W.npy", W)
np.save(outdir / "centroids_deg.npy", cent_deg)
pd.DataFrame({"trajectory_id": sub.trajectory_id.to_numpy(),
              "cluster": labels}).to_parquet(outdir / "subsample_labels.parquet",
                                             index=False)
(outdir / "fit_metadata.json").write_text(json.dumps({
    "source_notebook": "1.5_Manual_clustering.ipynb",
    "K": K,
    "DAY_WEIGHTS": {str(k): v for k, v in _wd.items()},
    "DAYS": C.DAYS,
    "N_SUB": C.N_SUB,
    "RANDOM_STATE": C.RANDOM_STATE,
    "n_fitted": int(len(sub)),
    "cluster_sizes": sizes.tolist(),
    "verified_against_notebook_fingerprint": True,
}, indent=2))
print(f"wrote -> {outdir}")
