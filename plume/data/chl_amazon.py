import copernicusmarine
from datetime import datetime

# Your credentials (consider using environment variables instead for security)
username = "dbarreto"
password = "DoNuT_120197"
output_directory = "chl"
# Loop through each year from 2000 to 2020
for year in range(2000, 2021):
    start_date = f"{year}-01-01T00:00:00"
    end_date = f"{year}-12-31T00:00:00"
    output_filename = f"{output_directory}/CHL_{year}.nc"  # NetCDF format
    
    print(f"Downloading year {year}...")
    
    copernicusmarine.subset(
        dataset_id="cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D",
        variables=["CHL"],
        username=username,
        password=password,
        minimum_longitude=-75,
        maximum_longitude=-35,
        minimum_latitude=-10,
        maximum_latitude=30,
        start_datetime=start_date,
        end_datetime=end_date,
        output_filename=output_filename,  # Saves with year-specific name
        force_download=True
    )
    
    print(f"Completed download for {year} as {output_filename}")

print("All downloads complete!")