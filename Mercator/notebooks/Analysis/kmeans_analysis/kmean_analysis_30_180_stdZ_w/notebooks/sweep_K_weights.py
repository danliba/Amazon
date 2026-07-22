"""Sweep K x DAY_WEIGHTS, scored on F resolution and cluster separation.

Why: the rerun fit put only 47.5% of the F (retroflection) route into a pure
cluster; the rest sits inside mixed clusters whose centroids look like C. The
route population itself is unchanged (0.966% of complete), so this is a
resolution problem, fixable with K and/or the weighting.

Ground truth for "is this trajectory F" comes from the ARCHIVED pre-rerun model
(data/kmeans_models/manual_1.5_k50/), clusters 8/14/45 - the definition that was
hand-verified on the panel grid. It encodes the whole route, not the endpoint,
which matters: an endpoint gate also catches C trajectories that loop mid-basin.

Metrics per configuration
  n_pure     clusters that are >=PURE_FRAC F                    (want >= 3)
  F_recall   share of all F trajectories sitting in those       (want high)
  F_prec     share of those clusters' members that are F
  sep        mean centroid-to-nearest-centroid distance, deg    (want high)
  min_n      smallest cluster                                   (watch for slivers)
"""
import sys, os, time, itertools, json
sys.path.insert(0, os.path.abspath(".."))
import numpy as np
import pandas as pd
import joblib
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
import config as C
import pipeline as P

PURE_FRAC = 0.80
K_GRID = [50, 75, 100, 150]
WEIGHTS = {
    "current":   {30: 0.5, 50: 1.5, 100: 1.0, 150: 1.5, 180: 2.0},
    "config":    {30: 0.5, 50: 2.0, 100: 1.5, 150: 1.0, 180: 2.0},
    "equal":     {30: 1.0, 50: 1.0, 100: 1.0, 150: 1.0, 180: 1.0},
    "endpoint":  {30: 0.5, 50: 1.0, 100: 1.0, 150: 1.5, 180: 3.0},
    "retrofl":   {30: 2.0, 50: 2.0, 100: 1.0, 150: 1.0, 180: 2.0},
    "U_strong":  {30: 1.0, 50: 2.0, 100: 0.5, 150: 2.0, 180: 3.0},
}

t0 = time.time()
features = pd.read_parquet(C.FEATURES_FILE)
complete = features[features.status == "complete"]
sub = complete.sample(n=min(C.N_SUB, len(complete)),
                      random_state=C.RANDOM_STATE).reset_index(drop=True)
X_raw = P.build_feature_matrix(sub)
scaler = StandardScaler().fit(X_raw)          # weights act after standardizing
Xs = scaler.transform(X_raw)
print(f"loaded {len(sub):,} trajectories in {time.time()-t0:.0f}s", flush=True)

# --- F ground truth from the archived model ---------------------------------
d = C.MODELS_DIR / "manual_1.5_k50"
okm, osc, oW = (joblib.load(d / "kmeans_k50.pkl"), joblib.load(d / "scaler.pkl"),
                np.load(d / "weights_W.npy"))
isF = np.isin(okm.predict(osc.transform(X_raw) * oW), [8, 14, 45])
nF = int(isF.sum())
print(f"F ground truth: {nF:,} trajectories ({100*isF.mean():.3f}%)\n", flush=True)

rows = []
for name, wd in WEIGHTS.items():
    W = np.array([np.sqrt(wd[dd]) for dd in C.DAYS for _ in range(2)])
    Xw = Xs * W
    for K in K_GRID:
        t = time.time()
        km = MiniBatchKMeans(n_clusters=K, random_state=C.RANDOM_STATE,
                             batch_size=10000, n_init=10, max_iter=300)
        lab = km.fit_predict(Xw)
        sizes = np.bincount(lab, minlength=K)

        fcount = np.bincount(lab[isF], minlength=K)
        frac = np.divide(fcount, np.maximum(sizes, 1))
        pure = frac >= PURE_FRAC
        n_pure = int(pure.sum())
        F_recall = fcount[pure].sum() / nF if nF else 0.0
        F_prec = fcount[pure].sum() / max(sizes[pure].sum(), 1)

        cent = P.centroids_to_degrees(km.cluster_centers_ / W, scaler)
        D = np.sqrt(((cent[:, None, :] - cent[None, :, :]) ** 2).sum(2))
        np.fill_diagonal(D, np.inf)
        sep = float(D.min(axis=1).mean())

        rows.append(dict(weights=name, K=K, n_pure=n_pure, F_recall=F_recall,
                         F_prec=F_prec, sep=sep, min_n=int(sizes.min()),
                         secs=time.time() - t))
        print(f"{name:9s} K={K:3d} | pure_F={n_pure:2d} recall={F_recall:5.1%} "
              f"prec={F_prec:5.1%} | sep={sep:5.2f} deg min_n={sizes.min():5d} "
              f"({time.time()-t:.0f}s)", flush=True)

r = pd.DataFrame(rows)
out = C.DATA_DIR / "sweep_K_weights.csv"
r.to_csv(out, index=False)
print(f"\nsaved -> {out}")

print("\n=== ranked by F recall into pure clusters ===")
print(r.sort_values(["F_recall", "sep"], ascending=False).head(12)
      .to_string(index=False, formatters={"F_recall": "{:.1%}".format,
                                          "F_prec": "{:.1%}".format,
                                          "sep": "{:.2f}".format,
                                          "secs": "{:.0f}".format}))
print(f"\nbaseline (what you have now): "
      f"{r[(r.weights=='current')&(r.K==50)].to_dict('records')}")
