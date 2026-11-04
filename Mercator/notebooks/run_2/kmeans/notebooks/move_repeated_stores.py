"""Retire the duplicate Zarr stores: 126 release dates were run twice.

Run segments overlap on release DATE, so those dates carry 20,000 particles
where every other date carries 10,000 - double weight in any k-means fit.
For each duplicated date this keeps the copy that integrates the full 180 days
and renames the other to `repeated_<date>.zarr`, which no longer matches
config.STORE_GLOB ("Parcels_run_*_*.zarr") and so drops out of list_stores()
for every project sharing DATA_ROOT.

Run with --apply to perform the renames; default is a dry run.
Writes a manifest so every rename can be undone.
"""
import sys, os, re, json
sys.path.insert(0, os.path.abspath(".."))
import pandas as pd
import config as C

APPLY = "--apply" in sys.argv
MANIFEST = C.PROJECT_ROOT / "data" / "repeated_stores_manifest.json"

stores = C.list_stores()
meta = []
for s in stores:
    m = re.match(r"Parcels_run_(\d+)_(\d{4}-\d{2}-\d{2})", s.stem)
    meta.append({"path": s, "run": m.group(1), "date": m.group(2)})
df = pd.DataFrame(meta)

dupdates = df.date.value_counts()
dupdates = sorted(dupdates[dupdates > 1].index)
print(f"{len(stores)} stores | {df.date.nunique()} release dates | "
      f"{len(dupdates)} duplicated dates")

# keep the copy whose run integrates a full 180 days past that release;
# run 67891 stops at 2009-12-31, so it is the loser on every shared date.
LOSER_RUN = "67891"
moves = []
for d in dupdates:
    rows = df[df.date == d]
    runs = set(rows.run)
    assert LOSER_RUN in runs and len(runs) == 2, f"{d}: unexpected runs {runs}"
    src = rows[rows.run == LOSER_RUN].path.iloc[0]
    keep = rows[rows.run != LOSER_RUN].path.iloc[0]
    dst = src.parent / f"repeated_{d}.zarr"
    moves.append({"src": str(src), "dst": str(dst), "kept": str(keep), "date": d})

print(f"\nmoving {len(moves)} stores (all from run {LOSER_RUN}):")
for m in moves[:3] + moves[-3:]:
    print(f"  {os.path.basename(m['src'])}\n    -> {os.path.basename(m['dst'])}")
print(f"  ... ({len(moves)} total)")

collide = [m for m in moves if os.path.exists(m["dst"])]
assert not collide, f"destination already exists: {collide[:3]}"

if not APPLY:
    print("\nDRY RUN - nothing moved. Re-run with --apply")
    sys.exit(0)

for m in moves:
    os.rename(m["src"], m["dst"])
MANIFEST.write_text(json.dumps(moves, indent=1))
print(f"\nmoved {len(moves)} stores | manifest -> {MANIFEST}")
print(f"stores now visible to list_stores(): {len(C.list_stores())}")
