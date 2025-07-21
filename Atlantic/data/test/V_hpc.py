import sys
from datetime import datetime
import copernicusmarine

# --- Inputs ---
year = int(sys.argv[1])
username = "dbarreto"
password = "DoNuT_120197"  # ❗Consider storing this in a file or env var
output_directory = "/work/bk1450/b383184/Amazon/Atlantic/data/UVW/"
output_filename = f"{output_directory}/V_{year}.nc"

start_date = f"{year}-01-01T00:00:00"
end_date = f"{year}-12-31T00:00:00"

print(f"Downloading year {year}...")

copernicusmarine.subset(
    dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
    variables=["vo"],
    username=username,
    password=password,
    minimum_longitude=-100,
    maximum_longitude=0,
    minimum_latitude=-50,
    maximum_latitude=50,
    start_datetime=start_date,
    end_datetime=end_date,
    minimum_depth=0.494,  
    maximum_depth=5727.91,
    output_filename=output_filename,
    force_download=True
)

print(f"Completed download for {year} as {output_filename}")
