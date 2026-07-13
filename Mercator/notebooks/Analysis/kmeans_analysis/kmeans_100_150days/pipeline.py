"""Reusable, vectorised building blocks for the trajectory-clustering pipeline.

The notebooks import these helpers so the heavy / fiddly numerics live in one
tested place and the notebooks stay readable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

import config as C


# --------------------------------------------------------------------------- #
# Stage 1 : feature extraction
# --------------------------------------------------------------------------- #
def _nearest_valid_index(rel_days, target, valid, tol):
    """For each trajectory, index of the obs whose time is closest to `target`
    days after release, restricted to valid (non-deleted) observations.

    Parameters
    ----------
    rel_days : (N, obs) float   time of each obs in days since that traj's release
                                (NaN where the obs is missing / deleted).
    target   : float            target offset in days (e.g. 50 or 100).
    valid    : (N, obs) bool     True where the position is usable.
    tol      : float            max allowed |obs_time - target| in days.

    Returns
    -------
    idx     : (N,) int      chosen obs index (0 if none reached -- see `ok`).
    ok      : (N,) bool     True if a valid obs within `tol` of the target exists.
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
    # argmax on the reversed mask gives the first True from the end.
    rev_first = np.argmax(valid[:, ::-1], axis=1)
    last = obs - 1 - rev_first
    last[~valid.any(axis=1)] = -1
    return last


def extract_store_features(store_path, store_index):
    """Extract the day-50 / day-100 feature vector for every trajectory in one
    Zarr store and return a tidy DataFrame.

    Status definitions
    ------------------
    'complete'   : valid positions at both day 50 and day 100.
    'partial'    : valid at day 50 but deleted/truncated before day 100;
                   the last known position is used as the day-100 proxy.
    'early_loss' : never reached day 50 (deleted early, or store truncated).
    """
    ds = xr.open_zarr(store_path)
    lat = ds.lat.values            # (N, obs) float64, NaN after deletion
    lon = ds.lon.values
    time = ds.time.values          # (N, obs) datetime64, NaT after deletion
    n = lat.shape[0]

    release = time[:, 0]                                   # (N,) datetime64
    rel_days = (time - release[:, None]) / np.timedelta64(1, "D")  # (N,obs) float
    valid = ~np.isnat(time) & ~np.isnan(lon)

    i50, ok50 = _nearest_valid_index(rel_days, C.DAY_INTER, valid, C.TIME_TOL_DAYS)
    i100, ok100 = _nearest_valid_index(rel_days, C.DAY_END, valid, C.TIME_TOL_DAYS)
    last = _last_valid_index(valid)

    rows = np.arange(n)
    lat50 = lat[rows, i50]
    lon50 = lon[rows, i50]
    lat100 = lat[rows, i100]
    lon100 = lon[rows, i100]

    # status -------------------------------------------------------------
    status = np.full(n, "complete", dtype=object)
    status[~ok100] = "partial"
    status[~ok50] = "early_loss"

    # partial: substitute last-known position for the missing day-100 point
    partial = (~ok100) & ok50
    if partial.any():
        pl = last[partial]
        lat100[partial] = lat[rows[partial], pl]
        lon100[partial] = lon[rows[partial], pl]

    # early_loss day-50/day-100 features are meaningless -> NaN
    lat50[~ok50] = np.nan
    lon50[~ok50] = np.nan
    lat100[~ok50] = np.nan
    lon100[~ok50] = np.nan

    release_time = pd.to_datetime(release)
    gid = store_index * C.TRAJ_PER_STORE + ds.trajectory.values

    df = pd.DataFrame(
        {
            "trajectory_id": gid.astype(np.int64),
            "store": store_path.stem,
            "lat_50": lat50.astype(np.float32),
            "lon_50": lon50.astype(np.float32),
            "lat_100": lat100.astype(np.float32),
            "lon_100": lon100.astype(np.float32),
            "release_time": release_time,
            "release_month": release_time.month.astype(np.int16),
            "release_year": release_time.year.astype(np.int16),
            "status": pd.Categorical(
                status, categories=["complete", "partial", "early_loss"]
            ),
        }
    )
    return df


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

    These (x, y, z) are a *horizontal* geometry embedding -- the z axis is the
    polar (north-south) axis, NOT ocean depth.  Straight-line (Euclidean)
    distance in this space is the chord, a monotonic function of the great-circle
    (haversine) distance, so plain k-means here clusters by true spherical
    distance and produces haversine-consistent centroids.
    """
    la = np.deg2rad(np.asarray(lat, dtype=np.float64))
    lo = np.deg2rad(np.asarray(lon, dtype=np.float64))
    x = np.cos(la) * np.cos(lo)
    y = np.cos(la) * np.sin(lo)
    z = np.sin(la)
    return x, y, z


def xyz_to_latlon(x, y, z):
    """Inverse of `latlon_to_xyz`.  Re-normalises onto the unit sphere first, so
    a 3-D centroid (which sits *inside* the sphere) is projected back to the
    proper surface location.  Returns (lat_deg, lon_deg)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    r = np.sqrt(x * x + y * y + z * z)
    r = np.where(r == 0, 1.0, r)
    lat = np.rad2deg(np.arcsin(np.clip(z / r, -1.0, 1.0)))
    lon = np.rad2deg(np.arctan2(y, x))
    return lat, lon


def build_feature_matrix(df):
    """Turn the 4 position columns into the X matrix used by k-means.

    FEATURE_SPACE == 'xyz' (default, haversine-correct):
        each position -> unit-sphere (x, y, z); X has 6 columns
        [x50, y50, z50, x100, y100, z100].
    FEATURE_SPACE == 'cosine' (legacy, near-equator approximation):
        X has 4 columns [lat50, lon50*f, lat100, lon100*f] with f = cos(MEAN_LAT).
    """
    if getattr(C, "FEATURE_SPACE", "xyz") == "xyz":
        x50, y50, z50 = latlon_to_xyz(df["lat_50"], df["lon_50"])
        x100, y100, z100 = latlon_to_xyz(df["lat_100"], df["lon_100"])
        return np.column_stack([x50, y50, z50, x100, y100, z100])

    f = lon_correction()
    return np.column_stack(
        [
            df["lat_50"].to_numpy(np.float64),
            df["lon_50"].to_numpy(np.float64) * f,
            df["lat_100"].to_numpy(np.float64),
            df["lon_100"].to_numpy(np.float64) * f,
        ]
    )


def apply_group_map(labels, group_map, k):
    """Map raw k-means cluster labels -> merged group ids.

    `group_map` is {raw_cluster_id: group_id}.  Any raw cluster not present in
    the map keeps its own identity as a singleton group.  Group ids are then
    densified to a contiguous 0..G-1 range (sorted) so colormaps behave.

    Labels of -1 (early_loss / unlabelled) are passed through unchanged.

    Returns (group_labels, raw_to_group) where raw_to_group is the resolved,
    densified mapping for every raw cluster 0..k-1.
    """
    resolved = {c: group_map.get(c, c) for c in range(k)}
    # densify the group ids actually used
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

    Use this as a starting point for GROUP_MAP; refine by eye. Operates in the
    active feature space (xyz or cosine), so the merge distances are sensible.
    """
    from scipy.cluster.hierarchy import fcluster, linkage

    Z = linkage(centers, method="ward")
    grp = fcluster(Z, t=n_groups, criterion="maxclust") - 1  # 0-based
    return {c: int(g) for c, g in enumerate(grp)}, Z


def centroids_to_degrees(centers):
    """Convert k-means centroids back to real degrees for plotting/tables.
    Returns columns [lat50, lon50, lat100, lon100] regardless of FEATURE_SPACE.

    For 'xyz' this re-projects each 3-D centroid onto the sphere (the proper
    spherical / haversine centroid); for 'cosine' it just undoes the lon factor.
    """
    centers = np.asarray(centers, dtype=np.float64)
    space = getattr(C, "FEATURE_SPACE", "xyz")
    ncol = centers.shape[1]
    expected = 6 if space == "xyz" else 4
    if ncol != expected:
        raise ValueError(
            f"FEATURE_SPACE='{space}' expects {expected}-column centroids but the "
            f"model has {ncol}. The saved k-means model was fit in a different "
            f"feature space. Re-run notebook 02 (refit) and notebook 03 (relabel) "
            f"so the models/labels match config.FEATURE_SPACE."
        )
    if space == "xyz":
        lat50, lon50 = xyz_to_latlon(centers[:, 0], centers[:, 1], centers[:, 2])
        lat100, lon100 = xyz_to_latlon(centers[:, 3], centers[:, 4], centers[:, 5])
        return np.column_stack([lat50, lon50, lat100, lon100])

    f = lon_correction()
    out = centers.copy()
    out[:, 1] /= f
    out[:, 3] /= f
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
