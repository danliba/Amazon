"""Evaluate radius sets x weightings: how many separated, reproducible pathways
per K.  Usage: python eval_configs.py <configs.json> [n_jobs]
Each config: {"name":..., "radii":[...], "weights":{r: w}}.
Fair comparison: same balanced samples (per seed) for every config, and pathway
distances always measured at the same yardstick radii YR, whatever radii the
clustering used."""
import sys, os, json, time, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import numpy as np, pandas as pd
import config as C, pipeline as P
from joblib import Parallel, delayed

EXP = C.DATA_DIR / "experiments"
KS = [50, 100, 150, 200, 300, 400, 500]
SEEDS = [42, 1, 7]
N_SUB = 500_000
SEP_KM, MATCH_KM = 400, 200
LOW_LAT = 8.0          # eastward pathways ending south of this = retroflection toward the equator / NECC
YR = [200, 500, 1000, 1500, 2000]

def lc(r): return f"lat_{r}km"
def oc(r): return f"lon_{r}km"

def load():
    f = pd.read_parquet(EXP / "features_dense.parquet")
    f = f[f.status.isin(["complete", "partial"])].reset_index(drop=True)
    b = P.bearing_deg(f.cross_lat, f.cross_lon, f[lc(2000)], f[oc(2000)])
    sector = np.clip(np.floor((b + 180) / 15).astype(int), 0, 23)
    n = np.bincount(sector, minlength=24)
    w = n[sector] ** -1.0                                  # alpha = 0: every sector equally
    samples = {s: np.random.default_rng(s).choice(len(f), min(N_SUB, len(f)), replace=False, p=w / w.sum())
               for s in SEEDS}
    Y = np.column_stack([f[c].to_numpy(np.float64) for r in YR for c in (lc(r), oc(r))])
    return f, b, samples, Y

def track_dist(A, B):
    nr = A.shape[1] // 2
    return sum(P.haversine_km(A[:, None, 2*j], A[:, None, 2*j+1], B[None, :, 2*j], B[None, :, 2*j+1])
               for j in range(nr)) / nr

def evaluate(cfg):
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.preprocessing import StandardScaler
    from scipy.cluster.hierarchy import linkage, fcluster
    from scipy.spatial.distance import squareform
    f, b, samples, Y = DATA
    radii = cfg["radii"]; wts = {int(k): v for k, v in cfg["weights"].items()}
    X = np.column_stack([f[c].to_numpy(np.float64) for r in radii for c in (lc(r), oc(r))])
    Wv = np.array([np.sqrt(wts[r]) for r in radii for _ in range(2)])
    start = f.cross_lon.to_numpy()
    rows = []
    for k in KS:
        res = {}
        for s in SEEDS:
            idx = samples[s]
            sc = StandardScaler().fit(X[idx])
            km = MiniBatchKMeans(n_clusters=k, random_state=s, batch_size=10000, n_init=10,
                                 max_iter=300).fit(sc.transform(X[idx]) * Wv)
            lab = km.labels_
            cent = pd.DataFrame(Y[idx]).groupby(lab).mean().reindex(range(k)).to_numpy()
            slon = pd.Series(start[idx]).groupby(lab).mean().reindex(range(k)).to_numpy()
            g = fcluster(linkage(squareform(track_dist(cent, cent), checks=False), "complete"),
                         t=SEP_KM, criterion="distance") - 1
            pt = np.array([cent[g == i].mean(0) for i in range(g.max() + 1)])
            ps = np.array([slon[g == i].mean() for i in range(g.max() + 1)])
            bear = P.bearing_deg(C.LAT_CROSS, ps, pt[:, -2], pt[:, -1])   # crossing -> 2000 km point
            D = track_dist(pt, pt); np.fill_diagonal(D, np.inf)
            res[s] = (pt, bear, D.min(1), ps)
        for s in SEEDS:
            pt, bear, nn, ps = res[s]
            ok = np.all([track_dist(pt, res[o][0]).min(1) < MATCH_KM for o in SEEDS if o != s], axis=0)
            east = bear > 0
            low = pt[:, -2] < LOW_LAT                       # ends south of LOW_LAT (NECC / toward the equator)
            sectors = np.unique(np.clip(np.floor((bear[ok] + 180) / 15), 0, 23))
            rows.append(dict(config=cfg["name"], K=k, seed=s, pathways=len(pt), reproduced=int(ok.sum()),
                             east_reproduced=int((ok & east).sum()),
                             east_low_reproduced=int((ok & east & low).sum()),
                             sectors=int(len(sectors)),
                             nn_median_km=float(np.median(nn[ok])) if ok.sum() > 1 else np.nan))
            np.savez(EXP / "results" / "tracks" / f"{cfg['name']}_K{k}_s{s}.npz",
                     tracks=pt, start_lon=ps, bearing=bear, reproduced=ok, yardstick=np.array(YR))
    out = pd.DataFrame(rows)
    out.to_csv(EXP / "results" / f"{cfg['name']}.csv", index=False)
    return out

if __name__ == "__main__":
    cfgs = json.load(open(sys.argv[1]))
    n_jobs = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    cfgs = [c for c in cfgs if not (EXP / "results" / f"{c['name']}.csv").exists()]
    DATA = load()
    print(f"{len(DATA[0]):,} particles to fit; {len(cfgs)} configs to run", flush=True)
    t0 = time.time()
    # fork-based processes share DATA without copying
    from multiprocessing import get_context
    with get_context("fork").Pool(n_jobs) as pool:
        for out in pool.imap_unordered(evaluate, cfgs):
            m = out.groupby("K")[["reproduced", "east_reproduced", "east_low_reproduced", "sectors"]].mean()
            print(f"{out.config.iloc[0]:20s} K: pathways/eastward/east-low/sectors  "
                  + "  ".join(f"{k}:{r.reproduced:.0f}/{r.east_reproduced:.0f}/{r.east_low_reproduced:.0f}/{r.sectors:.0f}"
                              for k, r in m.iterrows())
                  + f"  ({(time.time()-t0)/60:.0f} min)", flush=True)
