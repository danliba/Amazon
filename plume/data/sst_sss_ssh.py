import copernicusmarine

copernicusmarine.subset(
  dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
  variables=["so", "thetao", "zos"],
  minimum_longitude=-75,
  maximum_longitude=-30,
  minimum_latitude=-10,
  maximum_latitude=30,
  start_datetime="2000-01-01T00:00:00",
  end_datetime="2000-12-31T00:00:00",
  minimum_depth=0.49402499198913574,
  maximum_depth=0.49402499198913574,
)

