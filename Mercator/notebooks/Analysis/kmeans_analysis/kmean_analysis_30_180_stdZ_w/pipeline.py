"""Reusable, vectorised building blocks for the trajectory-clustering pipeline.

This is the **z-standardized, N-day** variant.  Positions are extracted at each
day in `config.DAYS` (default 50 / 100 / 150) and clustered on the RAW
[lat, lon] features after standardizing every column to mean 0, std 1 (done by a
StandardScaler in notebook 02, saved to `data/kmeans_models/scaler.pkl`).  There
is no spherical (xyz / haversine) embedding here: standardization is what gives
every day equal weight in the Euclidean distance.

The notebooks import these helpers so the heavy / fiddly numerics live in one
tested place and the notebooks stay readable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

import config as C


# --------------------------------------------------------------------------- #
# Feature-column bookkeeping
# --------------------------------------------------------------------------- #
def feature_columns():
    """Ordered position columns used to build the k-means matrix:
    [lat_<d0>, lon_<d0>, lat_<d1>, lon_<d1>, ...] for every day in C.DAYS."""
    cols = []
    for d in C.DAYS:
        cols += [f"lat_{d}", f"lon_{d}"]
    return cols


def feature_weight_vector():
    """Per-column multiplier that applies `config.DAY_WEIGHTS` to a standardized
    feature matrix, aligned to `feature_columns()`.

    Each day `d` contributes `cols_per_day` columns (2 for zscore/cosine, 3 for
    xyz).  Every one of that day's columns is multiplied by `sqrt(w_d)` so the
    day's SQUARED-distance contribution to the k-means objective is scaled by
    exactly `w_d`.  Used identically at fit time (nb 02), predict time (nb 03)
    and when converting centroids back to degrees (nb 02/04, which divide by it).

    Returns a 1-D float array of length `len(feature_columns())`.  If
    `config.DAY_WEIGHTS` is absent, returns all ones (pure equal weighting).
    """
    weights = getattr(C, "DAY_WEIGHTS", None)
    space = getattr(C, "FEATURE_SPACE", "zscore")
    cols_per_day = 3 if space == "xyz" else 2
    if not weights:
        return np.ones(cols_per_day * len(C.DAYS), dtype=np.float64)
    missing = [d for d in C.DAYS if d not in weights]
    if missing:
        raise ValueError(f"config.DAY_WEIGHTS is missing entries for days {missing}")
    return np.array([np.sqrt(weights[d]) for d in C.DAYS for _ in range(cols_per_day)],
                    dtype=np.float64)


# --------------------------------------------------------------------------- #
# Stage 1 : feature extraction
# --------------------------------------------------------------------------- #
def _nearest_valid_index(rel_days, target, valid, tol):
    """For each trajectory, index of the obs whose time is closest to `target`
    days after release, restricted to valid (non-deleted) observations.

    Returns
    -------
    idx : (N,) int   chosen obs index (0 if none reached -- see `ok`).
    ok  : (N,) bool  True if a valid obs within `tol` of the target exists.
    """
    dist = np.abs(rel_days - target)
    dist[~valid] = np.inf
    dist[np.isnan(dist)] = np.inf
    idx = dist.argmin(axis=1)
    rows = np.arange(idx.size)
    ok = dist[rows, idx] <= tol
    return idx, ok


def _last_valid_index(valid):
    """Index of the last valid observation for each trajectory (-1 if none)."""
    obs = valid.shape[1]
    rev_first = np.argmax(valid[:, ::-1], axis=1)
    last = obs - 1 - rev_first
    last[~valid.any(axis=1)] = -1
    return last


def extract_store_features(store_path, store_index):
    """Extract the day-by-day feature vector (one lat/lon pair per day in
    `config.DAYS`) for every trajectory in one Zarr store; return a tidy
    DataFrame.

    Status definitions (with DAYS = [50, 100, 150])
    ------------------------------------------------
    'complete'   : valid position at every day in DAYS.
    'partial'    : valid at the gate day (DAYS[0]) but deleted/truncated before
                   one or more later days; the last known position is used as the
                   proxy for each missing later day.
    'early_loss' : never reached the gate day (deleted early, or store truncated);
                   all position features are NaN.
    """
    ds = xr.open_zarr(store_path)
    lat = ds.lat.values            # (N, obs) float64, NaN after deletion
    lon = ds.lon.values
    time = ds.time.values          # (N, obs) datetime64, NaT after deletion
    n = lat.shape[0]

    release = time[:, 0]                                   # (N,) datetime64
    rel_days = (time - release[:, None]) / np.timedelta64(1, "D")  # (N,obs) float
    valid = ~np.isnat(time) & ~np.isnan(lon)
    rows = np.arange(n)
    last = _last_valid_index(valid)

    days = list(C.DAYS)
    idx = {}
    ok = {}
    for d in days:
        idx[d], ok[d] = _nearest_valid_index(rel_days, d, valid, C.TIME_TOL_DAYS)

    gate = days[0]
    ok_gate = ok[gate]
    all_ok = np.ones(n, dtype=bool)
    for d in days:
        all_ok &= ok[d]

    # status -------------------------------------------------------------
    status = np.full(n, "complete", dtype=object)
    status[ok_gate & ~all_ok] = "partial"
    status[~ok_gate] = "early_loss"

    data = {
        "trajectory_id": (store_index * C.TRAJ_PER_STORE
                          + ds.trajectory.values).astype(np.int64),
        "store": store_path.stem,
    }
    for d in days:
        la = lat[rows, idx[d]].astype(np.float64).copy()
        lo = lon[rows, idx[d]].astype(np.float64).copy()
        # partial: gate reached but this day missing -> last-known position proxy
        need = ok_gate & ~ok[d]
        if need.any():
            pl = last[need]
            la[need] = lat[rows[need], pl]
            lo[need] = lon[rows[need], pl]
        # early_loss: features meaningless -> NaN
        la[~ok_gate] = np.nan
        lo[~ok_gate] = np.nan
        data[f"lat_{d}"] = la.astype(np.float32)
        data[f"lon_{d}"] = lo.astype(np.float32)

    release_time = pd.to_datetime(release)
    data["release_time"] = release_time
    data["release_month"] = release_time.month.astype(np.int16)
    data["release_year"] = release_time.year.astype(np.int16)
    data["status"] = pd.Categorical(
        status, categories=["complete", "partial", "early_loss"]
    )
    return pd.DataFrame(data)


# --------------------------------------------------------------------------- #
# Stage 2/3 : feature matrix construction
# --------------------------------------------------------------------------- #
def lon_correction():
    """Cosine factor applied to longitudes before clustering (1.0 if disabled).
    Only used when FEATURE_SPACE == 'cosine'."""
    if C.MEAN_LAT is None:
        return 1.0
    return float(np.cos(np.deg2rad(C.MEAN_LAT)))


def latlon_to_xyz(lat, lon):
    """Map surface lat/lon (degrees) to unit-sphere Cartesian coordinates.
    Only used when FEATURE_SPACE == 'xyz' (legacy)."""
    la = np.deg2rad(np.asarray(lat, dtype=np.float64))
    lo = np.deg2rad(np.asarray(lon, dtype=np.float64))
    x = np.cos(la) * np.cos(lo)
    y = np.cos(la) * np.sin(lo)
    z = np.sin(la)
    return x, y, z


def xyz_to_latlon(x, y, z):
    """Inverse of `latlon_to_xyz` (legacy 'xyz' space).  Returns (lat, lon)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    r = np.sqrt(x * x + y * y + z * z)
    r = np.where(r == 0, 1.0, r)
    lat = np.rad2deg(np.arcsin(np.clip(z / r, -1.0, 1.0)))
    lon = np.rad2deg(np.arctan2(y, x))
    return lat, lon


def build_feature_matrix(df):
    """Turn the position columns into the RAW X matrix for k-means.

    FEATURE_SPACE == 'zscore' (default, this project):
        raw geography -- one [lat, lon] pair per day in C.DAYS
        e.g. [lat50, lon50, lat100, lon100, lat150, lon150].
        Standardization to mean 0 / std 1 is applied SEPARATELY by the
        StandardScaler fit in notebook 02 (see `data/kmeans_models/scaler.pkl`);
        it is deliberately NOT baked in here so this returns interpretable
        degrees.
    FEATURE_SPACE == 'xyz'    (legacy): each position -> unit-sphere (x, y, z).
    FEATURE_SPACE == 'cosine' (legacy): [lat, lon*cos(MEAN_LAT)] per day.
    """
    space = getattr(C, "FEATURE_SPACE", "zscore")
    if space == "xyz":
        blocks = []
        for d in C.DAYS:
            x, y, z = latlon_to_xyz(df[f"lat_{d}"], df[f"lon_{d}"])
            blocks += [x, y, z]
        return np.column_stack(blocks)

    if space == "cosine":
        f = lon_correction()
        blocks = []
        for d in C.DAYS:
            blocks.append(df[f"lat_{d}"].to_numpy(np.float64))
            blocks.append(df[f"lon_{d}"].to_numpy(np.float64) * f)
        return np.column_stack(blocks)

    # zscore (default): raw lat/lon, standardized downstream by StandardScaler.
    return df[feature_columns()].to_numpy(np.float64)


def apply_group_map(labels, group_map, k):
    """Map raw k-means cluster labels -> merged group ids.

    `group_map` is {raw_cluster_id: group_id}.  Any raw cluster not present in
    the map keeps its own identity as a singleton group.  Group ids are then
    densified to a contiguous 0..G-1 range (sorted) so colormaps behave.

    Labels of -1 (early_loss / unlabelled) are passed through unchanged.

    Returns (group_labels, raw_to_group).
    """
    resolved = {c: group_map.get(c, c) for c in range(k)}
    used = sorted(set(resolved.values()))
    dense = {g: i for i, g in enumerate(used)}
    raw_to_group = {c: dense[g] for c, g in resolved.items()}

    out = np.asarray(labels).copy()
    mask = out >= 0
    out[mask] = np.array([raw_to_group[c] for c in out[mask]])
    return out, raw_to_group


def suggest_groups(centers, n_groups):
    """Hierarchical (Ward) clustering of the k-means centroids -> a suggested
    {raw_cluster_id: group_id} map that merges the `centers` into `n_groups`.

    Operates in the ACTIVE model space (the standardized space for 'zscore'), so
    the merge distances match the space k-means was fit in.
    """
    from scipy.cluster.hierarchy import fcluster, linkage

    Z = linkage(centers, method="ward")
    grp = fcluster(Z, t=n_groups, criterion="maxclust") - 1  # 0-based
    return {c: int(g) for c, g in enumerate(grp)}, Z


def centroids_to_degrees(centers, scaler=None):
    """Convert k-means centroids back to real degrees for plotting/tables.
    Returns one [lat, lon] pair per day in C.DAYS, i.e. columns
    [lat_<d0>, lon_<d0>, lat_<d1>, lon_<d1>, ...].

    FEATURE_SPACE == 'zscore': `centers` live in standardized space, so the
        fitted StandardScaler MUST be passed to undo the standardization
        (inverse_transform) back to degrees.
    FEATURE_SPACE == 'xyz'/'cosine': legacy inverse of the embedding.
    """
    centers = np.asarray(centers, dtype=np.float64)
    space = getattr(C, "FEATURE_SPACE", "zscore")
    ncol = centers.shape[1]

    if space == "zscore":
        expected = 2 * len(C.DAYS)
        if ncol != expected:
            raise ValueError(
                f"zscore expects {expected}-column centroids (2 per day for "
                f"DAYS={list(C.DAYS)}) but the model has {ncol}. Re-run notebook "
                f"02 (refit) and 03 (relabel) so models match config."
            )
        if scaler is None:
            raise ValueError(
                "centroids_to_degrees needs the fitted StandardScaler for "
                "FEATURE_SPACE='zscore'. Load data/kmeans_models/scaler.pkl and "
                "pass it as `scaler=`."
            )
        return scaler.inverse_transform(centers)

    if space == "xyz":
        expected = 3 * len(C.DAYS)
        if ncol != expected:
            raise ValueError(
                f"FEATURE_SPACE='xyz' expects {expected}-column centroids but the "
                f"model has {ncol}. Re-run notebooks 02 and 03."
            )
        out = []
        for j in range(len(C.DAYS)):
            lat, lon = xyz_to_latlon(centers[:, 3 * j], centers[:, 3 * j + 1],
                                     centers[:, 3 * j + 2])
            out += [lat, lon]
        return np.column_stack(out)

    # cosine (legacy)
    f = lon_correction()
    out = centers.copy()
    out[:, 1::2] /= f
    return out


# --------------------------------------------------------------------------- #
# Stage 4 : transit-time helper
# --------------------------------------------------------------------------- #
def first_crossing_days(store_path, lat_thresh=None, lon_thresh=None):
    """Days-since-release at which each trajectory first crosses a lat or lon
    threshold.  NaN if never crossed.  One of lat_thresh / lon_thresh is given.

    Returns an (N,) array aligned with the store's trajectory order.
    """
    ds = xr.open_zarr(store_path)
    time = ds.time.values
    release = time[:, 0]
    rel_days = (time - release[:, None]) / np.timedelta64(1, "D")
    if lat_thresh is not None:
        coord = ds.lat.values
        crossed = coord >= lat_thresh
    else:
        coord = ds.lon.values
        crossed = coord <= lon_thresh
    crossed &= ~np.isnan(coord)
    rel = np.where(crossed, rel_days, np.inf)
    first = rel.argmin(axis=1)
    rows = np.arange(first.size)
    out = rel[rows, first]
    out[np.isinf(out)] = np.nan
    return out
