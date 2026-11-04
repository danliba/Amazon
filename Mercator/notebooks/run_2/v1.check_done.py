"""Print the offsets of a job range that are NOT done yet.
usage: python v1.check_done.py <first> <last> <seed>
A release is done when its executed notebook finished (papermill end_time set, no exception, every
code cell executed) and its zarr exists in tracks_v3_<seed>/.
A release is running (also not printed) when its executed notebook has no end_time yet and was
written in the last 4 h (the job time limit).
"""
import json, os, sys, time
import datetime as dt

first, last, seed = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
ref = dt.date(1993, 1, 1)


def notebook_done(path):
    try:
        nb = json.load(open(path))
    except Exception:
        return False
    pm = nb.get('metadata', {}).get('papermill', {})
    code = [c for c in nb['cells'] if c['cell_type'] == 'code' and ''.join(c['source']).strip()]
    return bool(pm.get('end_time')) and not pm.get('exception') and all(c.get('execution_count') for c in code)


def notebook_running(path):
    try:
        nb = json.load(open(path))
    except Exception:
        return False
    pm = nb.get('metadata', {}).get('papermill', {})
    return not pm.get('end_time') and not pm.get('exception') and time.time() - os.path.getmtime(path) < 4 * 3600


todo = []
for o in range(first, last + 1, 5):
    nbs = [f'executed/v3.Run_parcels_UVW_adaptive.seed{seed}.offset{o}.ipynb']
    if seed == '11098723':          # 1993-1994 run, before the seed was in the name
        nbs.append(f'executed/v3.Run_parcels_UVW_adaptive.offset{o}.ipynb')
    zarr = f'tracks_v3_{seed}/Parcels_run_{seed}_{ref + dt.timedelta(days=o)} 00:00:00.zarr'
    if any(notebook_running(p) for p in nbs):
        print(f'offset {o} is running', file=sys.stderr)
    elif not (os.path.isdir(zarr) and any(notebook_done(p) for p in nbs)):
        todo.append(o)
print(' '.join(map(str, todo)))
