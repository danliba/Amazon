"""Reusable, vectorised building blocks for the RADIUS clustering pipeline.

Each particle is described by where it first gets farther than each radius in
`config.RADII_KM` from the point where it first crossed `config.LAT_CROSS`
(haversine distance).  Those positions are standardized (StandardScaler, fit in
notebook 02 / 1.5) and re-weighted per radius (`config.RADIUS_WEIGHTS`) before
k-means, exactly like the day-based pipeline.

Particle identity
-----------------
Every row carries three columns that point at the real particle:

    store : Zarr store name (path stem)      -> which store to open
    row   : position inside that store       -> what to read (ds.lat.values[row])
    traj  : Parcels trajectory ID            -> to join with other run_2 outputs

run_2 stores had particles deleted, so the Parcels IDs have gaps and are NOT
row positions (e.g. IDs 4, 5, 8 sit in rows 0, 1, 2).  Always read by `row`;
`read_tracks` checks `ds.trajectory[row] == traj` on every read.
`trajectory_id` is only a running row number over the whole table (for joins);
nothing is decoded from it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

import config as C


# --------------------------------------------------------------------------- #
# Feature-column bookkeeping
# --------------------------------------------------------------------------- #
def lat_col(r):
    return f"lat_{r}km"


def lon_col(r):
    return f"lon_{r}km"


def days_col(r):
    return f"days_{r}km"


def feature_columns():
    """Ordered k-means columns: [lat_<r0>km, lon_<r0>km, lat_<r1>km, ...]."""
    cols = []
    for r in C.RADII_KM:
        cols += [lat_col(r), lon_col(r)]
    return cols


def feature_weight_vector(weights=None):
    """Per-column multiplier sqrt(w_r) aligned to `feature_columns()`.

    `weights` defaults to `config.RADIUS_WEIGHTS` (notebook 1.5 passes its own
    tuning dict).  Each radius has two columns, both multiplied by sqrt(w_r), so
    that radius' squared-distance contribution is scaled by exactly w_r.  Used
    identically at fit time, predict time, and when converting centroids back
    to degrees (divide by it).
    """
    weights = C.RADIUS_WEIGHTS if weights is None else weights
    missing = [r for r in C.RADII_KM if r not in weights]
    if missing:
        raise ValueError(f"weights are missing entries for radii {missing}")
    return np.array([np.sqrt(weights[r]) for r in C.RADII_KM for _ in range(2)],
                    dtype=np.float64)


# --------------------------------------------------------------------------- #
# Geometry (haversine on a sphere of radius C.EARTH_RADIUS_KM)
# --------------------------------------------------------------------------- #
def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km (broadcasts; NaN in -> NaN out)."""
    la1, lo1, la2, lo2 = (np.deg2rad(np.asarray(a, dtype=np.float64))
                          for a in (lat1, lon1, lat2, lon2))
    a = (np.sin((la2 - la1) / 2) ** 2
         + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2)
    return 2 * C.EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def bearing_deg(lat1, lon1, lat2, lon2):
    """Initial bearing from point 1 to point 2, degrees clockwise from north
    in (-180, 180]: 0 = N, 90 = E, -90 = W."""
    la1, lo1, la2, lo2 = (np.deg2rad(np.asarray(a, dtype=np.float64))
                          for a in (lat1, lon1, lat2, lon2))
    dlo = lo2 - lo1
    y = np.sin(dlo) * np.cos(la2)
    x = np.cos(la1) * np.sin(la2) - np.sin(la1) * np.cos(la2) * np.cos(dlo)
    return np.rad2deg(np.arctan2(y, x))


def circle_latlon(lat0, lon0, radius_km, n=361):
    """Points on the circle of `radius_km` around (lat0, lon0), for plotting."""
    la0, lo0 = np.deg2rad(lat0), np.deg2rad(lon0)
    th = np.deg2rad(np.linspace(0, 360, n))
    d = radius_km / C.EARTH_RADIUS_KM
    la = np.arcsin(np.sin(la0) * np.cos(d) + np.cos(la0) * np.sin(d) * np.cos(th))
    lo = lo0 + np.arctan2(np.sin(th) * np.sin(d) * np.cos(la0),
                          np.cos(d) - np.sin(la0) * np.sin(la))
    return np.rad2deg(la), np.rad2deg(lo)


# --------------------------------------------------------------------------- #
# Crossing + radius exits (shared by notebook 00 and Stage 1)
# --------------------------------------------------------------------------- #
def first_crossing(lat, lat0=None):
    """First output where a particle goes from south of `lat0` to at/north of it.

    Same rule as analysis/particle_diagnostics/Regroup_particles.ipynb:
    ``(lat.shift(obs=1) < lat0) & (lat >= lat0)``.  NaN comparisons are False,
    so deleted positions never count as a crossing.

    Returns
    -------
    k0      : (N,) int   obs index of the crossing (0 where not crossed).
    crossed : (N,) bool
    """
    lat0 = C.LAT_CROSS if lat0 is None else lat0
    with np.errstate(invalid="ignore"):
        cross = (lat[:, :-1] < lat0) & (lat[:, 1:] >= lat0)
    crossed = cross.any(axis=1)
    k0 = np.where(crossed, cross.argmax(axis=1) + 1, 0)
    return k0, crossed


def distance_from_crossing(lat, lon, k0, crossed):
    """(N, obs) haversine km from each particle's own crossing point; NaN before
    the crossing, after deletion, and for particles that never cross."""
    rows = np.arange(lat.shape[0])
    d = haversine_km(lat[rows, k0][:, None], lon[rows, k0][:, None], lat, lon)
    obs = np.arange(lat.shape[1])[None, :]
    d[(obs < k0[:, None]) | ~crossed[:, None]] = np.nan
    return d


def first_exit(dist, radii):
    """For each radius, the first obs with distance >= radius.

    Returns idx (N, nR) int (0 where not reached) and reached (N, nR) bool.
    """
    n, nr = dist.shape[0], len(radii)
    idx = np.zeros((n, nr), dtype=np.int64)
    reached = np.zeros((n, nr), dtype=bool)
    with np.errstate(invalid="ignore"):
        for j, r in enumerate(radii):
            hit = dist >= r
            reached[:, j] = hit.any(axis=1)
            idx[:, j] = np.where(reached[:, j], hit.argmax(axis=1), 0)
    return idx, reached


def _last_valid_index(valid):
    """Index of the last valid observation per trajectory (-1 if none)."""
    obs = valid.shape[1]
    last = obs - 1 - np.argmax(valid[:, ::-1], axis=1)
    last[~valid.any(axis=1)] = -1
    return last


# --------------------------------------------------------------------------- #
# Stage 1 : feature extraction
# --------------------------------------------------------------------------- #
STATUSES = ["complete", "partial", "no_gate", "no_cross"]


def extract_store_features(store_path):
    """One row per trajectory of one store: identity, crossing, and the exit
    position (+ days since crossing) at every radius in `config.RADII_KM`.

    Status
    ------
    'complete' : reached every radius.
    'partial'  : reached the gate radius (RADII_KM[0]) but the track ended
                 before one or more larger radii; the last known position is
                 used for each missing radius (its days_<r>km stays NaN).
    'no_gate'  : crossed LAT_CROSS but never got RADII_KM[0] away; features NaN.
    'no_cross' : never crossed LAT_CROSS; features NaN.
    Only 'complete' is used to fit; 'complete' + 'partial' get labels.
    """
    ds = xr.open_zarr(store_path)
    lat = ds.lat.values.astype(np.float64)     # (N, obs), NaN after deletion
    lon = ds.lon.values.astype(np.float64)
    time = ds.time.values                      # (N, obs) datetime64, NaT after deletion
    traj = ds.trajectory.values.astype(np.int64)
    n = lat.shape[0]
    rows = np.arange(n)

    k0, crossed = first_crossing(lat)
    dist = distance_from_crossing(lat, lon, k0, crossed)
    idx, reached = first_exit(dist, C.RADII_KM)
    valid = ~np.isnat(time) & ~np.isnan(lon) & ~np.isnan(lat)
    last = _last_valid_index(valid)

    gate = reached[:, 0]
    status = np.full(n, "complete", dtype=object)
    status[gate & ~reached.all(axis=1)] = "partial"
    status[crossed & ~gate] = "no_gate"
    status[~crossed] = "no_cross"

    release = time[:, 0]
    t_cross = np.where(crossed, time[rows, k0], np.datetime64("NaT"))
    data = {
        "store": store_path.stem,
        "row": rows.astype(np.int32),
        "traj": traj,
        "release_time": pd.to_datetime(release),
        "cross_time": pd.to_datetime(t_cross),
        "cross_obs": np.where(crossed, k0, -1).astype(np.int32),
        "cross_lat": np.where(crossed, lat[rows, k0], np.nan).astype(np.float32),
        "cross_lon": np.where(crossed, lon[rows, k0], np.nan).astype(np.float32),
        "days_to_cross": ((t_cross - release) / np.timedelta64(1, "D")).astype(np.float32),
        "r_last_km": np.where(crossed, dist[rows, last], np.nan).astype(np.float32),
    }
    for j, r in enumerate(C.RADII_KM):
        k = np.where(reached[:, j], idx[:, j], last)     # missing radius -> last position
        la = lat[rows, k].copy()
        lo = lon[rows, k].copy()
        la[~gate] = np.nan
        lo[~gate] = np.nan
        dd = (time[rows, idx[:, j]] - t_cross) / np.timedelta64(1, "D")
        dd = np.where(reached[:, j], dd, np.nan)
        data[lat_col(r)] = la.astype(np.float32)
        data[lon_col(r)] = lo.astype(np.float32)
        data[days_col(r)] = dd.astype(np.float32)

    df = pd.DataFrame(data)
    df["release_month"] = df.release_time.dt.month.astype(np.int16)
    df["release_year"] = df.release_time.dt.year.astype(np.int16)
    df["cross_month"] = df.cross_time.dt.month.fillna(0).astype(np.int16)  # 0 = never crossed
    df["cross_year"] = df.cross_time.dt.year.fillna(0).astype(np.int16)
    df["status"] = pd.Categorical(status, categories=STATUSES)
    return df


# --------------------------------------------------------------------------- #
# Reading full tracks back for chosen particles
# --------------------------------------------------------------------------- #
def read_tracks(store_path, rows, trajs, variables=("lon", "lat")):
    """Full tracks of the particles at `rows` of one store.

    Checks that the store's Parcels IDs at those rows equal `trajs`, so a stale
    features file or a re-written store fails loudly instead of silently
    returning other particles.  Returns one (len(rows), obs) array per variable.
    """
    ds = xr.open_zarr(store_path)
    rows = np.asarray(rows, dtype=np.int64)
    got = ds.trajectory.values[rows]
    if not np.array_equal(got, np.asarray(trajs, dtype=got.dtype)):
        raise ValueError(f"{store_path.name}: Parcels IDs at the requested rows do "
                         f"not match the features file - re-run notebook 01.")
    return [ds[v].values[rows] for v in variables]


def read_paths(pick, n_jobs=16, variables=("lon", "lat")):
    """{trajectory_id: (var0[obs], var1[obs], ...)} for every row of `pick`
    (needs columns trajectory_id, store, row, traj).  Each store is opened once;
    reads run in a thread pool (I/O-bound, blosc releases the GIL)."""
    from joblib import Parallel, delayed

    paths = C.store_paths_by_name()

    def _one(name, grp):
        arrs = read_tracks(paths[name], grp.row.to_numpy(), grp.traj.to_numpy(),
                           variables)
        return grp.trajectory_id.to_numpy(), arrs

    res = Parallel(n_jobs=n_jobs, backend="threading")(
        delayed(_one)(name, grp) for name, grp in pick.groupby("store", observed=True))
    out = {}
    for tids, arrs in res:
        for j, tid in enumerate(tids):
            out[int(tid)] = tuple(a[j] for a in arrs)
    return out


# --------------------------------------------------------------------------- #
# Stage 2/3 : feature matrix, grouping, centroids
# --------------------------------------------------------------------------- #
def build_feature_matrix(df):
    """Raw [lat, lon] per radius in degrees (standardized later by the saved
    StandardScaler, so this stays interpretable)."""
    return df[feature_columns()].to_numpy(np.float64)


def apply_group_map(labels, group_map, k):
    """Map raw k-means labels -> merged group ids (0..G-1, sorted).  Clusters
    not in `group_map` stay their own group; -1 passes through unchanged.
    Returns (group_labels, raw_to_group)."""
    resolved = {c: group_map.get(c, c) for c in range(k)}
    used = sorted(set(resolved.values()))
    dense = {g: i for i, g in enumerate(used)}
    raw_to_group = {c: dense[g] for c, g in resolved.items()}

    out = np.asarray(labels).copy()
    mask = out >= 0
    out[mask] = np.array([raw_to_group[c] for c in out[mask]])
    return out, raw_to_group


def suggest_groups(centers, n_groups):
    """Ward clustering of the k-means centroids (in the space k-means was fit
    in) -> suggested {raw_cluster_id: group_id} map and the linkage matrix."""
    from scipy.cluster.hierarchy import fcluster, linkage

    Z = linkage(centers, method="ward")
    grp = fcluster(Z, t=n_groups, criterion="maxclust") - 1
    return {c: int(g) for c, g in enumerate(grp)}, Z


def centroids_to_degrees(centers, scaler):
    """Standardized centroids (already divided by the weight vector) -> degrees,
    columns [lat_<r0>km, lon_<r0>km, ...]."""
    centers = np.asarray(centers, dtype=np.float64)
    expected = 2 * len(C.RADII_KM)
    if centers.shape[1] != expected:
        raise ValueError(f"expected {expected}-column centroids (2 per radius in "
                         f"{C.RADII_KM}) but got {centers.shape[1]}; refit.")
    return scaler.inverse_transform(centers)
