# import copernicusmarine

# copernicusmarine.subset(
#   dataset_id="cmems_mod_glo_phy_anfc_0.083deg_P1D-m",
#   dataset_version="202406",
#   variables=["zos"],
#   minimum_longitude=-180,
#   maximum_longitude=179.9169921875,
#   minimum_latitude=-80,
#   maximum_latitude=90,
#   start_datetime="2025-09-10T00:00:00",
#   end_datetime="2025-09-10T00:00:00",
#   minimum_depth=0.49402499198913574,
#   maximum_depth=0.49402499198913574,
#   coordinates_selection_method="strict-inside",
#   netcdf_compression_level=1,
#   disable_progress_bar=True,
# )

import os
from datetime import datetime
import copernicusmarine
import calendar
from concurrent.futures import ThreadPoolExecutor, as_completed

username = "dbarreto"
password = "DoNuT_120197"
output_directory = "/work/bk1450/b383184/Amazon/Atlantic/data/tracers/"

def download_month(year, month):
    try:
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01T00:00:00"
        end_date = f"{year}-{month:02d}-{last_day:02d}T23:59:59"
        output_filename = f"{output_directory}/ssh_{year}_{month:02d}.nc"

        # Skip if file already exists
        if os.path.exists(output_filename):
            print(f"Task {os.environ.get('SLURM_PROCID', 0)}: Skipping existing file: {output_filename}")
            return

        print(f"Task {os.environ.get('SLURM_PROCID', 0)}: Downloading: {output_filename}")

        copernicusmarine.subset(
            dataset_id="cmems_mod_glo_phy_anfc_0.083deg_P1D-m",
            variables=["zos"],
            username=username,
            password=password,
            minimum_longitude=-100,
            maximum_longitude=0,
            minimum_latitude=-50,
            maximum_latitude=50,
            start_datetime=start_date,
            end_datetime=end_date,
            output_filename=output_filename
        )

        print(f"Task {os.environ.get('SLURM_PROCID', 0)}: Completed: {output_filename}")
    except Exception as e:
        print(f"Task {os.environ.get('SLURM_PROCID', 0)}: Error downloading {year}-{month:02d}: {e}")

# Create all tasks - FIXED LOGIC
all_tasks = []
for iy in range(2022, 2025 + 1):
    imost = 6 if iy == 2022 else 1  # Start from June for 2022, January for others
    for imo in range(imost, 12 + 1):
        all_tasks.append((iy, imo))

# Debug: print all tasks from task 0
task_id = int(os.environ.get('SLURM_PROCID', 0))
total_tasks = int(os.environ.get('SLURM_NTASKS', 1))

if task_id == 0:
    print(f"Total months to download: {len(all_tasks)}")
    print(f"All tasks: {all_tasks}")

# Distribute work among SLURM tasks
tasks_per_slurm_task = len(all_tasks) // total_tasks
remainder = len(all_tasks) % total_tasks

# Give extra task to first 'remainder' processes
if task_id < remainder:
    start_idx = task_id * (tasks_per_slurm_task + 1)
    end_idx = start_idx + tasks_per_slurm_task + 1
else:
    start_idx = remainder * (tasks_per_slurm_task + 1) + (task_id - remainder) * tasks_per_slurm_task
    end_idx = start_idx + tasks_per_slurm_task

my_tasks = all_tasks[start_idx:end_idx]

print(f"SLURM task {task_id}/{total_tasks}: handling {len(my_tasks)} months: {my_tasks}")

# Use threading within each SLURM task
MAX_THREADS = 2  # 2 threads per SLURM task
with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    futures = [executor.submit(download_month, year, month) for year, month in my_tasks]
    for f in as_completed(futures):
        pass