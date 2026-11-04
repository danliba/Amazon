"""Same members as check_box_reentry.py; how do exits change if the NBC box is
enlarged by MARGIN degrees on every side?"""
import sys, os, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import numpy as np, pandas as pd, config as C, pipeline as P
from joblib import Parallel, delayed
MARGINS = ["0", "S1", "SE1", "SE2"]   # degrees added to the south (S) and east (E) sides
mt = pd.read_csv(C.DATA_DIR / "experiments" / "box_reentry_members.csv")
f = pd.read_parquet(C.FEATURES_FILE, columns=["trajectory_id", "store", "row", "traj", "cross_obs"])
pick = mt[["trajectory_id", "pathway"]].merge(f, on="trajectory_id"); del f
share = pd.read_csv(C.DATA_DIR / "experiments" / "box_reentry_summary.csv").set_index("pathway").pct_particles
def seq(lo, la, m):
    ok = ~(np.isnan(lo) | np.isnan(la)); lo, la = lo[ok], la[ok]
    a = {"0": (0, 0, 0, 0), "S1": (0, 0, 1, 0), "SE1": (0, 1, 1, 0), "SE2": (0, 2, 2, 0)}[m]   # W, E, S, N
    b = dict(lon0=-55 - a[0], lon1=-45 + a[1], lat0=5 - a[2], lat1=10 + a[3])
    ins = (lo >= b["lon0"]) & (lo <= b["lon1"]) & (la >= b["lat0"]) & (la <= b["lat1"])
    def side(x, y):
        d = {"N": y - b["lat1"], "S": b["lat0"] - y, "W": b["lon0"] - x, "E": x - b["lon1"]}
        return max(d, key=d.get)
    return [side(lo[k+1], la[k+1]) for k in range(len(ins)-1) if ins[k] and not ins[k+1]]
paths = C.store_paths_by_name()
def one(name, g):
    lo_all, la_all = P.read_tracks(paths[name], g.row.to_numpy(), g.traj.to_numpy())
    out = []
    for (_, r), lo, la in zip(g.iterrows(), lo_all, la_all):
        for m in MARGINS:
            ex = seq(lo[r.cross_obs:], la[r.cross_obs:], m)
            out.append(dict(pathway=r.pathway, margin=m, n_exits=len(ex), n_sides=len(set(ex)),
                            first=ex[0] if ex else "-"))
    return out
res = Parallel(n_jobs=32, backend="loky")(delayed(one)(n, g) for n, g in pick.groupby("store", observed=True))
d = pd.DataFrame([x for r in res for x in r])
d["same_again"] = (d.n_exits >= 2) & (d.n_sides == 1); d["change"] = d.n_sides >= 2
per = d.groupby(["margin", "pathway"])[["same_again", "change"]].mean().mul(100).reset_index()
per["w"] = per.pathway.map(share)
tot = per.groupby("margin").apply(lambda x: pd.Series({
    "same side again % (all particles)": (x.same_again * x.w).sum() / x.w.sum(),
    "change side % (all particles)": (x.change * x.w).sum() / x.w.sum(),
    "pathways with >25% same-side wiggles": int((x.same_again > 25).sum()),
    "pathways with >25% side changes": int((x.change > 25).sum())})).round(1)
print(tot.to_string())
fe = d.groupby(["margin", "pathway"])["first"].agg(lambda s: s.value_counts(normalize=True).iloc[0] * 100).unstack(0).round(0)
print("\nhow consistent is the FIRST exit side within each pathway (% of members with the most common first side):")
print(fe.loc[share.sort_values(ascending=False).index].to_string())
