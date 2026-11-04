"""Transfer the hand grouping (cluster_K50_GROUPED.pdf) onto the K=70 fit.

Source: the archived pre-rerun K=50 centroids + the letters annotated on
cluster_K50_GROUPED.pdf. Target: the current fit (K=70, n_init=100).
Each new centroid inherits the letter of its nearest old centroid, using the
same metric as cell 16 (Euclidean over the full centroid track, degrees).
"""
import sys, os
sys.path.insert(0, os.path.abspath(".."))
import numpy as np
import pandas as pd
import joblib
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
import config as C
import pipeline as P

K = 70
N_INIT = 100
DAY_WEIGHTS = {30: 0.5, 50: 1.5, 100: 1.0, 150: 1.5, 180: 2.0}
W = np.array([np.sqrt(DAY_WEIGHTS[d]) for d in C.DAYS for _ in range(2)])
EXPECTED = (1002, 94409)

# letters read off cluster_K50_GROUPED.pdf (differs from the notebook's ASSIGN
# at 9=S1, 10=B1, 34=B1)
PDF = {
    0:"A2",  1:"E1",  2:"B1",  3:"BS",  4:"E2",  5:"A2",  6:"C",   7:"B2",  8:"F",   9:"S1",
   10:"B1", 11:"B3", 12:"C",  13:"B2", 14:"F",  15:"S",  16:"A1", 17:"BS", 18:"E",  19:"S",
   20:"A2", 21:"E0", 22:"A2", 23:"B2", 24:"B3", 25:"S",  26:"CB", 27:"E2", 28:"B2", 29:"B2",
   30:"C",  31:"A1", 32:"E",  33:"A3", 34:"B1", 35:"A12",36:"A2", 37:"S",  38:"B2", 39:"A2",
   40:"B1", 41:"S",  42:"A2", 43:"BS", 44:"C",  45:"F",  46:"B2", 47:"CB", 48:"B1", 49:"E1",
}
assert len(PDF) == 50

features = pd.read_parquet(C.FEATURES_FILE)
complete = features[features.status == "complete"]
sub = complete.sample(n=min(C.N_SUB, len(complete)),
                      random_state=C.RANDOM_STATE).reset_index(drop=True)
X_raw = P.build_feature_matrix(sub)
scaler = StandardScaler().fit(X_raw)
km = MiniBatchKMeans(n_clusters=K, random_state=C.RANDOM_STATE,
                     batch_size=10000, n_init=N_INIT, max_iter=300)
labels = km.fit_predict(scaler.transform(X_raw) * W)
sizes = np.bincount(labels, minlength=K)
new_cent = P.centroids_to_degrees(km.cluster_centers_ / W, scaler)
got = (int(sizes.min()), int(sizes.max()))
print(f"fit k={K} n_init={N_INIT} | sizes {got[0]}..{got[1]} "
      f"{'(matches your run)' if got == EXPECTED else '!! DIFFERS from your run'}")

old_cent = np.load(C.MODELS_DIR / "manual_1.5_k50" / "centroids_deg.npy")

D = np.sqrt(((new_cent[:, None, :] - old_cent[None, :, :]) ** 2).sum(axis=2))
nearest, dist = D.argmin(axis=1), D.min(axis=1)
margin = np.partition(D, 1, axis=1)[:, 1] - dist

rows = []
for c in range(K):
    o = int(nearest[c]); runner = int(np.argsort(D[c])[1])
    rows.append(dict(new=c, n=int(sizes[c]), letter=PDF[o], old=o, dist=dist[c],
                     margin=margin[c], runner_letter=PDF[runner]))
t = pd.DataFrame(rows)

# F check against the archived model's definition
d = C.MODELS_DIR / "manual_1.5_k50"
okm, osc, oW = (joblib.load(d/"kmeans_k50.pkl"), joblib.load(d/"scaler.pkl"),
                np.load(d/"weights_W.npy"))
isF = np.isin(okm.predict(osc.transform(X_raw) * oW), [8, 14, 45])
fc = np.bincount(labels[isF], minlength=K)
t["F_pct"] = (100 * fc / np.maximum(sizes, 1)).round(1)
t["F_share"] = (100 * fc / isF.sum()).round(1)

print(f"\nmatch distance: median {np.median(dist):.1f}  90th {np.percentile(dist,90):.1f}"
      f"  max {dist.max():.1f} deg")
amb = t[(t.margin < 2.0) & (t.letter != t.runner_letter)]
print(f"ambiguous (different-letter runner-up within 2 deg): {sorted(amb.new)}")

print("\nclusters the transfer calls F:")
print(t[t.letter == "F"][["new","n","dist","F_pct","F_share"]].to_string(index=False))
print(f"  -> they hold {t[t.letter=='F'].F_share.sum():.1f}% of the real F route")

print("\ngroup sizes:")
g = t.groupby("letter").agg(clusters=("new","size"), traj=("n","sum"))
print(g.sort_index().to_string())
lost = sorted(set(PDF.values()) - set(t.letter))
if lost:
    print(f"\nletters with no cluster in the new fit: {lost}")

t.to_csv(C.DATA_DIR / "grouping_transfer_k70.csv", index=False)
np.save(C.DATA_DIR / "new_centroids_deg_k70.npy", new_cent)
print(f"\nsaved -> {C.DATA_DIR/'grouping_transfer_k70.csv'}")

print("\nASSIGN = {")
for r in range(0, K, 10):
    print("   " + " ".join(f'{c}:"{t.letter[c]}",'.ljust(10)
                           for c in range(r, min(r+10, K))).rstrip())
print("}")
