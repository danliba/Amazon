"""Rank evaluated configs.  usage: python summarize.py [stage2 <n_random>]

Criteria (means over K = 50..500 and 3 seeds, reproducible pathways only):
  faces    : how many different sides of the NBC box (55-45W, 5-10N) the
             pathways leave through (N, W, E, S) - routes in different directions
  sectors  : how many 15-degree outer-direction sectors they cover
  eastward : pathways whose crossing -> 2000 km direction is east of north
  east_low : eastward and ending south of 8N (retroflection / toward the equator)
  pathways : all reproducible pathways (>= 400 km apart)
Rank: faces, eastward, east_low, pathways, then sectors (faces and sectors saturate: all
configs use the N, W and E sides; sector means differ by < 0.5, i.e. noise).
"""
import sys, json, glob, re, numpy as np, pandas as pd
from pathlib import Path

BOX = dict(lon0=-55.0, lon1=-45.0, lat0=5.0, lat1=10.0)
LAT_CROSS = 2.5

def inside(lo, la):
    return BOX["lon0"] <= lo <= BOX["lon1"] and BOX["lat0"] <= la <= BOX["lat1"]

def exit_face(lons, lats):
    """Side of the box through which the polyline first leaves it after entering.
    'none' = never inside, 'stays' = still inside at its last point."""
    was_in = False
    for k in range(len(lons) - 1):
        p, q = (lons[k], lats[k]), (lons[k + 1], lats[k + 1])
        if inside(*p):
            was_in = True
            if not inside(*q):
                ts = {}
                dx, dy = q[0] - p[0], q[1] - p[1]
                if dy > 0: ts["N"] = (BOX["lat1"] - p[1]) / dy
                if dy < 0: ts["S"] = (BOX["lat0"] - p[1]) / dy
                if dx < 0: ts["W"] = (BOX["lon0"] - p[0]) / dx
                if dx > 0: ts["E"] = (BOX["lon1"] - p[0]) / dx
                return min(ts, key=ts.get)
        elif not was_in:
            # entering on this segment? then continue from the entry point
            if inside(*q):
                was_in = True
            else:
                # segment may cross the whole box: sample it finely
                for t in np.linspace(0, 1, 50)[1:-1]:
                    x, y = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
                    if inside(x, y):
                        sub = np.linspace(t, 1, 50)
                        xs, ys = p[0] + sub * (q[0] - p[0]), p[1] + sub * (q[1] - p[1])
                        return exit_face(list(xs), list(ys))
    return "stays" if was_in else "none"

def faces_of(npz):
    d = np.load(npz)
    pt, st, ok = d["tracks"], d["start_lon"], d["reproduced"]
    out = []
    for i in np.where(ok)[0]:
        lons = np.r_[st[i], pt[i, 1::2]]; lats = np.r_[LAT_CROSS, pt[i, 0::2]]
        out.append(exit_face(list(lons), list(lats)))
    return out

res = pd.concat([pd.read_csv(f) for f in glob.glob("results/*.csv")], ignore_index=True)
frows = []
for f in glob.glob("results/tracks/*.npz"):
    m_ = re.match(r"(.+)_K(\d+)_s(\d+)\.npz", Path(f).name)
    fl = faces_of(f)
    frows.append(dict(config=m_.group(1), K=int(m_.group(2)), seed=int(m_.group(3)),
                      faces=len({x for x in fl if x in "NWES"}),
                      **{f"exit_{s}": fl.count(s) for s in ("N", "W", "E", "S", "none", "stays")}))
res = res.merge(pd.DataFrame(frows), on=["config", "K", "seed"], how="left")
res.to_csv("all_results.csv", index=False)

cols = ["faces", "sectors", "east_reproduced", "east_low_reproduced", "reproduced",
        "exit_N", "exit_W", "exit_E", "exit_S", "exit_none", "exit_stays"]
m = res.groupby(["config", "K"])[cols].mean().reset_index()
ref = m[(m.config == "cur_userweights") & (m.K == 400)].iloc[0]
rows = []
for c, d in m.groupby("config"):
    d = d.sort_values("K")
    reach = d[(d.faces >= ref.faces) & (d.sectors >= ref.sectors) & (d.east_reproduced >= ref.east_reproduced)].K
    rows.append(dict(config=c, faces=d.faces.mean(), sectors=d.sectors.mean(),
                     eastward=d.east_reproduced.mean(), east_low=d.east_low_reproduced.mean(),
                     pathways=d.reproduced.mean(),
                     K_to_match_ref=int(reach.min()) if len(reach) else np.nan,
                     **{f"@{k} face/sect/east/low/all": "/".join(f"{v:.0f}" for v in d[d.K == k][
                         ["faces", "sectors", "east_reproduced", "east_low_reproduced", "reproduced"]].iloc[0])
                        for k in (100, 200, 300, 400, 500)},
                     **{f"exits N/W/E/S/none/stays @400": "/".join(f"{v:.0f}" for v in d[d.K == 400][
                         ["exit_N", "exit_W", "exit_E", "exit_S", "exit_none", "exit_stays"]].iloc[0])}))
tab = (pd.DataFrame(rows).sort_values(["faces", "eastward", "east_low", "pathways", "sectors"], ascending=False)
       .round(1))
tab["radii_set"] = tab.config.str.split("_").str[0]
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(f"reference = current radii + your weights at K=400: {ref.faces:.1f} box sides, {ref.sectors:.1f} sectors, "
      f"{ref.east_reproduced:.1f} eastward, {ref.east_low_reproduced:.1f} east-low, {ref.reproduced:.1f} pathways; "
      f"exits N/W/E/S/none/stays = {ref.exit_N:.0f}/{ref.exit_W:.0f}/{ref.exit_E:.0f}/{ref.exit_S:.0f}/"
      f"{ref.exit_none:.0f}/{ref.exit_stays:.0f}\n")
print(tab.drop(columns="radii_set").to_string(index=False))
tab.to_csv("ranking.csv", index=False)

if len(sys.argv) > 2 and sys.argv[1] == "stage2":
    cfg1 = {c["name"]: c for c in json.load(open("configs_stage1.json"))}
    best = tab[tab.config.isin(cfg1)].iloc[0]
    radii = cfg1[best.config]["radii"]
    rset = best.radii_set
    rng = np.random.default_rng(2026)
    out = []
    for i in range(int(sys.argv[2])):
        w = np.exp(rng.uniform(np.log(0.25), np.log(4), len(radii))); w = w / w.mean()
        out.append({"name": f"{rset}_rand{i:02d}", "radii": radii,
                    "weights": {int(r): round(float(x), 3) for r, x in zip(radii, w)}})
    # plus stronger "far radii count more" ramps, the direction the stage-1 winner points to
    r = np.array(radii, float)
    for p_ in (1.0, 1.5, 2.0):
        w = (r / r[-1]) ** p_; w = w / w.mean()
        out.append({"name": f"{rset}_backpow{p_:g}", "radii": radii,
                    "weights": {int(a): round(float(x), 3) for a, x in zip(radii, w)}})
    json.dump(out, open("configs_stage2.json", "w"), indent=1)
    print(f"\nstage 2: {len(out)} weightings on radii set '{rset}' {radii} (best stage-1 config: {best.config})")
