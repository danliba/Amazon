# import copernicusmarine

# copernicusmarine.subset(
#   dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m",
#   variables=["uo"],
#   minimum_longitude=-100,
#   maximum_longitude=0,
#   minimum_latitude=-50,
#   maximum_latitude=50,
#   start_datetime="2022-06-01T00:00:00",
#   end_datetime="2025-01-06T00:00:00",
#   minimum_depth=0.49402499198913574,
#   maximum_depth=5727.9169921875,
# )

import copernicusmarine
from datetime import datetime

# Your credentials (consider using environment variables instead for security)
username = "dbarreto"
password = "DoNuT_120197"
output_directory = "/work/bk1450/b383184/Amazon/Atlantic/data/UVW/"
# Loop through each year from 2022 to 2025
for year in range(2022, 2025+1):
    start_date = f"{year}-06-01T00:00:00"
    end_date = f"{year}-12-31T00:00:00"
    output_filename = f"{output_directory}/U_{year}.nc"  # NetCDF format
    
    print(f"Downloading year {year}...")
    
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
        minimum_depth=0.49402499198913574,  
        maximum_depth=5727.9169921875,
        output_filename=output_filename,  # Saves with year-specific name
        force_download=True
    )
    
    print(f"Completed download for {year} as {output_filename}")

print("All downloads complete!")