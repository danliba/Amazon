# U_hpc.py
import sys, calendar, os
from datetime import datetime
import copernicusmarine

# --- Inputs desde terminal ---
year = int(sys.argv[1])
month = int(sys.argv[2])

username = "dbarreto"
password = "DoNuT_120197"
output_directory = "/work/bk1450/b383184/Amazon/Atlantic/data/UV/"
# os.makedirs(output_directory, exist_ok=True)

last_day = calendar.monthrange(year, month)[1]
start_date = f"{year}-{month:02d}-01T00:00:00"
end_date = f"{year}-{month:02d}-{last_day:02d}T23:59:59"
output_filename = f"{output_directory}/V_{year}_{month:02d}.nc"

print(f" Downloading: {output_filename} from {start_date} to {end_date}")

try:
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
        minimum_depth=0.49402499198913574,
        maximum_depth=5727.9169921875,
        output_filename=output_filename,
        force_download=True
    )
    print(f"Completed: {output_filename}")
except Exception as e:
    print(f" Error downloading {year}-{month:02d}: {e}")
