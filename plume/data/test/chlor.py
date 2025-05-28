import copernicusmarine

copernicusmarine.subset(
  dataset_id="cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D",
  variables=["CHL_uncertainty"],
  minimum_longitude=-75,
  maximum_longitude=-35,
  minimum_latitude=-10,
  maximum_latitude=30,
  start_datetime="2000-01-01T00:00:00",
  end_datetime="2020-12-31T00:00:00",
)