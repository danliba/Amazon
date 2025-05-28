import copernicusmarine
from datetime import datetime

username = "dbarreto"
password = "DoNuT_120197"
output_directory = "salt"

# copernicusmarine.subset(
#   dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
#   variables=["so"],
#   minimum_longitude=-75,
#   maximum_longitude=-30,
#   minimum_latitude=-10,
#   maximum_latitude=30,
#   start_datetime="2000-01-01T00:00:00",
#   end_datetime="2020-12-31T00:00:00",
#   minimum_depth=0.49402499198913574,
#   maximum_depth=0.49402499198913574,
# )

# Loop through each year from 2000 to 2020
for year in range(2000, 2021):
    start_date = f"{year}-01-01T00:00:00"
    end_date = f"{year}-12-31T00:00:00"
    output_filename = f"{output_directory}/salt_{year}.nc"  # NetCDF format
    
    print(f"Downloading year {year}...")
    
    copernicusmarine.subset(
        dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
        variables=["so"],
        username=username,
        password=password,
        minimum_longitude=-75,
        maximum_longitude=-35,
        minimum_latitude=-10,
        maximum_latitude=30,
        start_datetime=start_date,
        end_datetime=end_date,
        minimum_depth=0.49402499198913574,
        maximum_depth=0.49402499198913574,
        output_filename=output_filename,  # Saves with year-specific name
        force_download=True
    )
    
    print(f"Completed download for {year} as {output_filename}")

print("All downloads complete!")