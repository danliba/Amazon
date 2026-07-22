"""Carry the manual grouping from the OLD k=50 fit onto the NEW one.

The store cleanup + notebook 01 rerun changed features.parquet, so notebook 1.5
converged to a different partition: cluster ids no longer mean what they meant
when the grid was hand-labelled. This reproduces the new fit, then matches each
NEW centroid to its nearest OLD centroid and inherits that cluster's letter.

The old centroids come from data/kmeans_models/manual_1.5_k50/ (archived before
the rerun). The distance is the same metric notebook 1.5 cell 16 uses: Euclidean
over the full centroid track in degrees.
"""
import sys, os, json
sys.path.insert(0, os.path.abspath(".."))
import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
import config as C
import pipeline as P

K = 50
DAY_WEIGHTS = {30: 0.5, 50: 1.5, 100: 1.0, 150: 1.5, 180: 2.0}
W = np.array([np.sqrt(DAY_WEIGHTS[d]) for d in C.DAYS for _ in range(2)])
EXPECTED_RANGE = (1406, 71799)          # printed by the user's rerun of 1.5

OLD_ASSIGN = {
    0:"A2",  1:"E1",  2:"B1",  3:"BS",  4:"E2",  5:"A2",  6:"C",   7:"B2",  8:"F",   9:"S",
   10:"B2", 11:"B3", 12:"C",  13:"B2", 14:"F",  15:"S",  16:"A1", 17:"BS", 18:"E",  19:"S",
   20:"A2", 21:"E0", 22:"A2", 23:"B2", 24:"B3", 25:"S",  26:"CB", 27:"E2", 28:"B2", 29:"B2",
   30:"C",  31:"A1", 32:"E",  33:"A3", 34:"B2", 35:"A12",36:"A2", 37:"S",  38:"B2", 39:"A2",
   40:"B1", 41:"S",  42:"A2", 43:"BS", 44:"C",  45:"F",  46:"B2", 47:"CB", 48:"B1", 49:"E1",
}

# --- reproduce the NEW fit (verbatim from 1.5 cells 1+3) ---------------------
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
new_cent = P.centroids_to_degrees(km.cluster_centers_ / W, scaler)
got = (int(sizes.min()), int(sizes.max()))
print(f"new fit: {len(sub):,} trajectories | cluster sizes {got[0]}..{got[1]}")
if got != EXPECTED_RANGE:
    print(f"  WARNING: expected {EXPECTED_RANGE} from your rerun - not the same fit!")
else:
    print("  matches your rerun of notebook 1.5")

old_cent = np.load(C.MODELS_DIR / "manual_1.5_k50" / "centroids_deg.npy")
print(f"old centroids: {old_cent.shape} (archived pre-rerun)")

# --- nearest old centroid for each new centroid ------------------------------
D = np.sqrt(((new_cent[:, None, :] - old_cent[None, :, :]) ** 2).sum(axis=2))
nearest = D.argmin(axis=1)
dist = D.min(axis=1)
second = np.partition(D, 1, axis=1)[:, 1]
margin = second - dist                    # how much better than runner-up

rows = []
for c in range(K):
    o = int(nearest[c])
    runner = int(np.argsort(D[c])[1])
    rows.append(dict(new=c, n=int(sizes[c]), letter=OLD_ASSIGN[o], old=o,
                     dist=dist[c], margin=margin[c],
                     runner_letter=OLD_ASSIGN[runner], runner=runner))
t = pd.DataFrame(rows)

print("\n=== proposed grouping for the NEW clusters ===")
print(t.to_string(index=False,
                  formatters={"dist": "{:.1f}".format, "margin": "{:.1f}".format}))

print("\n--- transfer quality ---")
print(f"match distance: median {np.median(dist):.1f} deg, "
      f"90th pct {np.percentile(dist,90):.1f}, max {dist.max():.1f}")
amb = t[(t.margin < 2.0) & (t.letter != t.runner_letter)]
far = t[t.dist > np.percentile(dist, 90)]
print(f"\nambiguous (runner-up within 2 deg AND a different letter): {len(amb)}")
if len(amb):
    print(amb[["new", "n", "letter", "dist", "runner_letter", "margin"]]
          .to_string(index=False, formatters={"dist": "{:.1f}".format,
                                              "margin": "{:.1f}".format}))
print(f"\nweakest matches (top 10% distance): {sorted(far.new.tolist())}")

print("\n--- group sizes, old vs new ---")
old_n = pd.Series(OLD_ASSIGN).value_counts().rename("old_clusters")
new_n = t.letter.value_counts().rename("new_clusters")
cmp = pd.concat([old_n, new_n], axis=1).fillna(0).astype(int)
cmp["new_traj"] = t.groupby("letter").n.sum()
print(cmp.sort_index().to_string())

lost = sorted(set(OLD_ASSIGN.values()) - set(t.letter))
if lost:
    print(f"\nLETTERS WITH NO NEW CLUSTER: {lost}")

out = C.DATA_DIR / "grouping_transfer_old_to_new.csv"
t.to_csv(out, index=False)
np.save(C.DATA_DIR / "new_centroids_deg.npy", new_cent)
print(f"\nsaved -> {out}")
print("\nASSIGN = {")
for r in range(0, K, 10):
    print("   " + " ".join(f'{c}:"{t.letter[c]}",'.ljust(10) for c in range(r, min(r+10, K))))
print("}")
