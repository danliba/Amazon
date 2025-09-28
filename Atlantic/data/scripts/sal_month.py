# import copernicusmarine

# copernicusmarine.subset(
#   dataset_id="cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m",
#   variables=["so"],
#   minimum_longitude=-100,
#   maximum_longitude=0,
#   minimum_latitude=-50,
#   maximum_latitude=50,
#   start_datetime="2022-06-01T00:00:00",
#   end_datetime="2025-09-17T00:00:00",
#   minimum_depth=0.49402499198913574,
#   maximum_depth=5727.9169921875,
# )

from datetime import datetime
import copernicusmarine
import calendar
from concurrent.futures import ThreadPoolExecutor, as_completed

username = "dbarreto"
password = "DoNuT_120197"
output_directory = "/work/bk1450/b383184/Amazon/Atlantic/data/tracers/sal"

# ====================================
def download_month(year, month):
    try:
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01T00:00:00"
        end_date = f"{year}-{month:02d}-{last_day:02d}T23:59:59"
        output_filename = f"{output_directory}/sal_{year}_{month:02d}.nc"

        print(f"Downloading: {output_filename} from {start_date} to {end_date}")

        copernicusmarine.subset(
            dataset_id="cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m", #temperature",
            variables=["so"],
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
            output_filename=output_filename
        )

        print(f"Completed: {output_filename}")
    except Exception as e:
        print(f"Error downloading {year}-{month:02d}: {e}")

# ====================================
# Crear lista de tareas
tasks = []
for iy in range(2022, 2025 + 1):
    imost = 1 if iy > 2022 else 6
    for imo in range(imost, 12 + 1):
        tasks.append((iy, imo))

# ====================================
# Lanzar tareas en paralelo
MAX_THREADS = 3  # o el número de CPUs que SLURM te da
with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    futures = [executor.submit(download_month, year, month) for year, month in tasks]
    for f in as_completed(futures):
        pass  # ya imprimimos dentro de la función