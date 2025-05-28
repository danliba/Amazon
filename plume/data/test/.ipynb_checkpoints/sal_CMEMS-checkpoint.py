#!/usr/bin/env python3
# download_cmems_data.py

import copernicusmarine
from datetime import datetime
import logging

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='download_cmems_data.log'
    )
    
    logging.info("Starting CMEMS data download")
    
    try:
        # Download the data
        copernicusmarine.subset(
            dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
            variables=["so"],
            minimum_longitude=-75,
            maximum_longitude=-30,
            minimum_latitude=-10,
            maximum_latitude=30,
            start_datetime="2000-01-01T00:00:00",
            end_datetime="2020-12-31T00:00:00",
            minimum_depth=0.49402499198913574,
            maximum_depth=0.49402499198913574,
        )
        logging.info("Data download completed successfully")
    except Exception as e:
        logging.error(f"Error during data download: {str(e)}")
        raise

if __name__ == "__main__":
    main()
