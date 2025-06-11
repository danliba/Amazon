import copernicusmarine

copernicusmarine.subset(
  dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
  variables=["uo", "vo"],
  minimum_longitude=-100,
  maximum_longitude=25,
  minimum_latitude=-60,
  maximum_latitude=80,
  start_datetime="1993-01-01T00:00:00",
  end_datetime="1993-01-02T00:00:00",
  minimum_depth=0.49402499198913574,
  maximum_depth=0.49402499198913574,
)