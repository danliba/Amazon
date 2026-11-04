"""Do pathways really leave the NBC box twice?  Refit v3.1.5 at K=400 exactly as
the notebook (same balanced sample, seed, weights -> same clusters/pathways),
label the particles of every 5th store, read up to N_PER members per pathway
and follow their REAL 6-hourly tracks after the 2.5N crossing through the box.
Output: data/experiments/box_reentry_members.csv (one row per checked particle)
and box_reentry_summary.csv (one row per pathway)."""
import sys, os, warnings, time
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import numpy as np, pandas as pd, xarray as xr
import config as C, pipeline as P
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from joblib import Parallel, delayed

K, SEED, N_SUB, SEP_KM, N_PER = 400, 42, 500_000, 400, 500
RW = {200: 0.027, 500: 0.166, 1000: 0.663, 1500: 1.492, 2000: 2.653}
BOX = dict(lon0=-55.0, lon1=-45.0, lat0=5.0, lat1=10.0)
OUT = C.DATA_DIR / "experiments"
t0 = time.time()

# --- same fit as v3.1.5 ------------------------------------------------------
f = pd.read_parquet(C.FEATURES_FILE)
fit = f[f.status.isin(["complete", "partial"])].reset_index(drop=True); del f
b = P.bearing_deg(fit.cross_lat, fit.cross_lon, fit[P.lat_col(2000)], fit[P.lon_col(2000)])
sector = np.clip(np.floor((b + 180) / 15).astype(int), 0, 23)
n_sec = np.bincount(sector, minlength=24)
w = n_sec[sector].astype(float) ** -1.0
idx = np.random.default_rng(SEED).choice(len(fit), size=min(N_SUB, len(fit)), replace=False, p=w / w.sum())
X_all = P.build_feature_matrix(fit)
W = P.feature_weight_vector(RW)
sc = StandardScaler().fit(X_all[idx])
km = MiniBatchKMeans(n_clusters=K, random_state=SEED, batch_size=10000, n_init=20, max_iter=300).fit(sc.transform(X_all[idx]) * W)
cent = pd.DataFrame(X_all[idx]).groupby(km.labels_).mean().reindex(range(K)).to_numpy()
def track_dist(A, B):
    nr = A.shape[1] // 2
    return sum(P.haversine_km(A[:, None, 2*j], A[:, None, 2*j+1], B[None, :, 2*j], B[None, :, 2*j+1]) for j in range(nr)) / nr
g = fcluster(linkage(squareform(track_dist(cent, cent), checks=False), "complete"), t=SEP_KM, criterion="distance") - 1
print(f"refit K={K}: {g.max()+1} pathways ({time.time()-t0:.0f}s)", flush=True)

# --- members: all particles of every 5th store --------------------------------
keep_stores = set()
for d in C.TRACK_DIRS:
    keep_stores |= {p.stem for p in sorted((C.DATA_ROOT / d).glob(C.STORE_GLOB))[::5]}
m = fit.store.astype(str).isin(keep_stores).to_numpy()
mem = fit.loc[m, ["trajectory_id", "store", "row", "traj", "cross_obs"]].copy()
mem["pathway"] = g[km.predict(sc.transform(X_all[m]) * W)]
share = mem.pathway.value_counts(normalize=True).sort_index() * 100
pick = pd.concat([d.sample(min(N_PER, len(d)), random_state=0) for _, d in mem.groupby("pathway")])
print(f"{len(mem):,} particles in {len(keep_stores)} stores; checking {len(pick):,} members "
      f"({pick.store.nunique()} stores) ({time.time()-t0:.0f}s)", flush=True)

# --- real tracks through the box ----------------------------------------------
def sequence(lo, la):
    ok = ~(np.isnan(lo) | np.isnan(la)); lo, la = lo[ok], la[ok]
    ins = (lo >= BOX["lon0"]) & (lo <= BOX["lon1"]) & (la >= BOX["lat0"]) & (la <= BOX["lat1"])
    def side(x, y):
        dd = {"N": y - BOX["lat1"], "S": BOX["lat0"] - y, "W": BOX["lon0"] - x, "E": x - BOX["lon1"]}
        return max(dd, key=dd.get)
    ex = [side(lo[k+1], la[k+1]) for k in range(len(ins)-1) if ins[k] and not ins[k+1]]
    return ex, bool(len(ins) and ins[-1])

paths = C.store_paths_by_name()
def one(name, grp):
    lo_all, la_all = P.read_tracks(paths[name], grp.row.to_numpy(), grp.traj.to_numpy())
    out = []
    for (_, r), lo, la in zip(grp.iterrows(), lo_all, la_all):
        ex, end_in = sequence(lo[r.cross_obs:], la[r.cross_obs:])
        out.append(dict(trajectory_id=r.trajectory_id, pathway=r.pathway, n_exits=len(ex),
                        sequence=(" → ".join(ex) if ex else ("stays" if end_in else "none"))
                                 + (" (ends inside)" if ex and end_in else "")))
    return out
res = Parallel(n_jobs=int(os.environ.get("SLURM_CPUS_PER_TASK", 16)), backend="loky")(
    delayed(one)(n, gg) for n, gg in pick.groupby("store", observed=True))
mt = pd.DataFrame([x for r in res for x in r])
mt.to_csv(OUT / "box_reentry_members.csv", index=False)

rows = []
for pth, d in mt.groupby("pathway"):
    vc = d.sequence.value_counts(normalize=True) * 100
    rows.append(dict(pathway=pth, pct_particles=round(share.get(pth, 0), 3), checked=len(d),
                     pct_leave_2plus=round(100 * (d.n_exits >= 2).mean(), 1),
                     pct_leave_once=round(100 * (d.n_exits == 1).mean(), 1),
                     top_sequences="; ".join(f"{s} {v:.0f}%" for s, v in vc.head(4).items())))
sm = pd.DataFrame(rows).sort_values("pct_particles", ascending=False)
sm.to_csv(OUT / "box_reentry_summary.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
print(sm.to_string(index=False))
w2 = (sm.pct_particles * sm.pct_leave_2plus / 100).sum() / sm.pct_particles.sum() * 100
print(f"\nall particles (weighted by pathway share): {w2:.1f}% leave the box 2+ times  ({time.time()-t0:.0f}s)")
