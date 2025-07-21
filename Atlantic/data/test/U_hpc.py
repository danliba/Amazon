import sys
import os
import calendar
from datetime import datetime
import copernicusmarine

# --- Inputs from SLURM ---
year = int(sys.argv[1])
month = int(sys.argv[2])

# --- Auth & config ---
username = "dbarreto"
password = "DoNuT_120197"
output_directory = "/work/bk1450/b383184/Amazon/Atlantic/data/UVW/"
# os.makedirs(output_directory, exist_ok=True)

# --- Date range ---
last_day = calendar.monthrange(year, month)[1]
start_date = f"{year}-{month:02d}-01T00:00:00"
end_date = f"{year}-{month:02d}-{last_day:02d}T23:59:59"
output_filename = os.path.join(output_directory, f"U_{year}_{month:02d}.nc")

print(f"Downloading: {output_filename}")
print(f"From: {start_date} to {end_date}")

try:
    copernicusmarine.subset(
        dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
        variables=["uo"],
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
    print(f"Completed: {output_filename}")
except Exception as e:
    print(f"Error downloading {year}-{month:02d}: {e}")


# username = "dbarreto"
# password = "DoNuT_120197"  # ❗Consider storing this in a file or env var
# output_directory = "/work/bk1450/b383184/Amazon/Atlantic/data/UVW/"
# output_filename = f"{output_directory}/U_{year}.nc"

# start_date = f"{year}-01-01T00:00:00"
# end_date = f"{year}-12-31T00:00:00"

# print(f"Downloading year {year}...")

# copernicusmarine.subset(
#     dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
#     variables=["uo"],
#     username=username,
#     password=password,
#     minimum_longitude=-100,
#     maximum_longitude=0,
#     minimum_latitude=-50,
#     maximum_latitude=50,
#     start_datetime=start_date,
#     end_datetime=end_date,
#     minimum_depth=0.494,  
#     maximum_depth=5727.91,
#     output_filename=output_filename,
#     force_download=True
# )

# print(f"Completed download for {year} as {output_filename}")
