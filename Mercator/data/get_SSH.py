import numpy as np
import pandas as pd
import xarray as xr
import os, pathlib, stat, textwrap
import calendar
import datetime
from datetime import date
from tqdm import tqdm

outpath = '/work/bk1450/b383184/Amazon/Mercator/data/variables_c/'

## URL
SSHfiles = "dap2://tds.mercator-ocean.fr/thredds/dodsC/glorys12v1-daily-grid2D"

## environment
os.environ["NETRC"] = "/home/b/b383184/.netrc"

## mesh
ds_Zgr = xr.open_dataset('../data/Zgr_mesh.nc')
ds_Hgr = xr.open_dataset('../data/Hgr_mesh.nc')

## functions - Cut the data
lon0, lon1 = -95, 10
lat0, lat1 = -10, 30

# 1) Use T-point lon/lat
lonT = ds_Hgr.glamt.isel(t=0)
latT = ds_Hgr.gphit.isel(t=0)

# 2) Build boolean mask for your box
mask = (lonT >= lon0) & (lonT <= lon1) & (latT >= lat0) & (latT <= lat1)

# 3) Get index ranges
yy, xx = np.where(mask.values)

y0, y1 = int(yy.min()), int(yy.max())
x0, x1 = int(xx.min()), int(xx.max())

x0, x1, y0, y1

##################################
## MERCATOR download function ####
##################################
def download_MERCATOR(url, varname, starts, ends, x0, x1, y0, y1, output_file):
    
    parts = []
    for tt in tqdm(range(len(days)//2)):
        da = (
            xr.open_dataset(url, engine="pydap", mask_and_scale=False, decode_cf=True)[varname]
            .sortby("time_counter")
            .isel(x=slice(x0, x1), y=slice(y0, y1))
            .sel(time_counter=slice(starts[tt], ends[tt]))
            .astype("float32")
            .load()
        )
        parts.append(da)
    
    da_all = xr.concat(parts, dim="time_counter")
    da_all = da_all.where(da_all!= 9.96921e+36,np.nan)
    da_all.to_dataset(name=varname).to_netcdf(output_file, unlimited_dims=["time_counter"])
    print(f"Saved {output_file}")

## Loop for year month
for year in range(1993,2000,1):
    for month in range(1,12+1,1):
        print(f'{year}-{month}')
        ## calendar dates
        last_day = calendar.monthrange(year, month)[1]
        start_date = datetime.datetime(year, month, 1)
        end_date = datetime.datetime(year, month, last_day)


        ## days in GLORYS
        def glorys_days(start_date, end_date):
            return pd.date_range(start=start_date, end=end_date, freq="D") + pd.Timedelta(hours=12)
        
        days = glorys_days(start_date.strftime("%Y-%m-%d")
                           , end_date.strftime("%Y-%m-%d"))
        #starts and ends
        starts = days[0::2]
        ends = days[1::2].tolist()  
        ends[-1] = days[-1]
        ends
        
        SSH_out = f'SSH_{start_date.strftime("%Y-%m-%d")[:7]}c.nc'

        download_MERCATOR(SSHfiles, "sossheig", starts, ends, x0, x1, y0, y1,outpath+SSH_out)






        
