from concurrent.futures import ThreadPoolExecutor, as_completed  # or ProcessPoolExecutor
import os
import calendar
import dask
from tqdm.dask import TqdmCallback
import xarray as xr
import numpy as np
import copernicusmarine

# -------------------------
# W calculator
# -------------------------
def prepare_ocean_dataset(ds):
    ds_i = ds
    _lat = ds.latitude
    _lon = ds.longitude
    _zt  = ds.depth

    ds_i = ds_i.rename({"depth": "k", "latitude":"j", "longitude":"i","uo":"uf", "vo":"vf"})
    ds_i = ds_i.assign_coords(
        k=np.arange(ds_i.sizes["k"]),
        j=np.arange(ds_i.sizes["j"]),
        i=np.arange(ds_i.sizes["i"]),
        depth_t=("k", _zt.data),
        latitude_f=("j", _lat.data),
        longitude_f=("i", _lon.data),
    )

    ds_i = ds_i.assign(fmask = ds_i.uf.isel(time=0, drop=True).notnull())

    ds_i = ds_i.assign(
        tmask=(
            ds_i.fmask.shift(i=0,  j=0)
            | ds_i.fmask.shift(i=-1, j=-1).fillna(False)
            | ds_i.fmask.shift(i=0,  j=-1).fillna(False)
            | ds_i.fmask.shift(i=-1, j=0 ).fillna(False)   # small fix: was duplicated
        ).astype(bool)
    )

    ds_i = ds_i.assign(
        u=(ds_i.uf.fillna(0) + ds_i.uf.shift(j=-1).fillna(0))/2,
        v=(ds_i.vf.fillna(0) + ds_i.vf.shift(i=-1).fillna(0))/2,
    )

    # Compute depth_w from depth_t
    zt = ds_i.depth_t.data
    zw = [zt[0]*2]
    for k in range(1, ds_i.sizes["k"]):
        zw.append((zt[k] - zw[k-1])*2 + zw[k-1])
    ds_i = ds_i.assign_coords(depth_w=("k", zw))

    ds_i = ds_i.assign_coords(
        longitude_u = ds_i.longitude_f,
        latitude_v  = ds_i.latitude_f,
        latitude_u  = ds_i.latitude_f + 1/12/2,
        longitude_v = ds_i.longitude_f + 1/12/2,
        latitude_t  = ds_i.latitude_f + 1/12/2,
        longitude_t = ds_i.longitude_f + 1/12/2,
    )

    R = 6371e3
    ds_i = ds_i.assign_coords(
        dz_t = ds_i.depth_w - ds_i.depth_w.shift(k=1).fillna(0),
        dx_t = np.deg2rad(1/12) * R * np.cos(np.deg2rad(ds_i.latitude_t)),
        dy_t = np.deg2rad(1/12) * R,
    )

    F_uv_vol = (
        ds_i.u * ds_i.dy_t * ds_i.dz_t - ds_i.u.shift(i=-1) * ds_i.dy_t * ds_i.dz_t
        + ds_i.v * ds_i.dx_t * ds_i.dz_t - ds_i.v.shift(j=-1) * ds_i.dx_t * ds_i.dz_t
    ).fillna(0)

    dw_by_dz = -F_uv_vol / ds_i.dx_t / ds_i.dy_t / ds_i.dz_t
    w = (dw_by_dz.fillna(0) * ds_i.dz_t.fillna(0)).cumsum('k').fillna(0).where(ds_i.tmask==1)

    tmask = ds_i.tmask  # keep lazy; no .compute() here
    w_bottom = w.isel(k=tmask.sum('k') - 1)
    w_correct = w - w_bottom / ds_i.dz_t.where(ds_i.tmask==1).sum('k') * ds_i.depth_w
    ds_i['w_c'] = w_correct

    ds_i = ds_i.drop_vars(['u','v','fmask','tmask'])
    return ds_i

# -----------------------------------
# Month-level processing (CALL THIS)
# -----------------------------------
def process_month(year, month,
                  output_path,
                  bbox=(-100, 0, -50, 50),
                  dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
                  dataset_version="202311",
                  variables=("vo", "uo"),
                  username=None, password=None):
    os.makedirs(output_path, exist_ok=True)

    last_day = calendar.monthrange(year, month)[1]
    start_date = f"{year}-{month:02d}-01T00:00:00"
    end_date   = f"{year}-{month:02d}-{last_day:02d}T23:59:59"

    # Download/open
    ds = copernicusmarine.open_dataset(
        dataset_id=dataset_id,
        minimum_longitude=bbox[0], maximum_longitude=bbox[1],
        minimum_latitude=bbox[2],  maximum_latitude=bbox[3],
        start_datetime=start_date, end_datetime=end_date,
        variables=list(variables),
        username=username, password=password,
        chunk_size_limit=-1
    )

    # Optional: ensure reasonable dask chunks for IO
    # ds = ds.chunk({'time': 2, 'depth': -1, 'latitude': 512, 'longitude': 512})

    ds_i = prepare_ocean_dataset(ds)

    # Files for this month
    var_to_file = {
        'uf': f'U_{start_date[:7]}.nc',
        'vf': f'V_{start_date[:7]}.nc',
        'w_c': f'W_{start_date[:7]}.nc',
    }

    tasks = []
    for vname, fname in var_to_file.items():
        fullpath = os.path.join(output_path, fname)
        da = ds_i[vname].astype('float32')  # optional downcast
        enc = {
            vname: {
                'zlib': True, 'complevel': 4,
                'chunksizes': (1, ds_i.sizes['k'], 512, 512),  # time,k,j,i
            }
        }
        tasks.append(
            da.to_dataset(name=vname).to_netcdf(
                fullpath, engine='h5netcdf', encoding=enc, compute=False
            )
        )

    # Progress bar for this month’s dask graph
    with TqdmCallback(desc=f"Writing {year}-{month:02d}"):
        dask.compute(*tasks)

# -----------------------------------
# Run several months in parallel
# -----------------------------------
# Prepare list of months
year_months = [(1993, m) for m in range(1, 4)]  # example: Jan–Mar 1993

# # Credentials (avoid hardcoding; consider env vars)
USERNAME = os.environ.get("CMEMS_USER", "dbarreto")
PASSWORD = os.environ.get("CMEMS_PASS", "DoNuT_120197")

OUTPUT_DIR = "/work/bk1450/b383184/Amazon/Atlantic/data/reanalysis"
MAX_WORKERS = 3  # adjust to your node limits

from concurrent.futures import ThreadPoolExecutor, as_completed
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
    futures = {
        ex.submit(process_month, y, m, OUTPUT_DIR,
                  username=USERNAME, password=PASSWORD): (y, m)
        for (y, m) in year_months
    }
    for fut in as_completed(futures):
        y, m = futures[fut]
        try:
            fut.result()
            print(f"Done {y}-{m:02d}")
        except Exception as e:
            print(f"Failed {y}-{m:02d}: {e}")