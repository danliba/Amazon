from parcels import ParticleSet
from parcels import JITParticle
from parcels import AdvectionRK4_3D
from parcels import AdvectionRK4
from parcels import Variable
from datetime import timedelta
import numpy as np
from parcels import FieldSet
from glob import glob
import sys

##-------load data for A native Copernicus grid
pathUV= '/work/bk1450/b383184/Amazon/Atlantic/data/UV'
pathW= '/work/bk1450/b383184/Amazon/Atlantic/data/W'

ufiles = sorted(glob(f"{pathUV}/U_20*.nc"))
vfiles = sorted(glob(f"{pathUV}/V_20*.nc"))
wfiles = sorted(glob(f"{pathW}/W_20*.nc"))

##-------- Particle set up
# number of particles
num_particles = 100_000

## Release location
lon = -48.9 * np.ones(shape=(num_particles, ))
lat = np.linspace(1.5, -1, num_particles)

lon0 = lon.mean()
lat0 = lat.mean()

x = lon - lon0
y = lat - lat0

theta = np.deg2rad(45)
x_rot = x * np.cos(theta) - y * np.sin(theta)
y_rot = x * np.sin(theta) + y * np.cos(theta)

lon_start = x_rot + lon0
lat_start = y_rot + lat0


## parameters

## set the tracking time
days = 700
minutes = 20

## record the particles every timestep of
hours=6

## define the fieldset
filenames = {"U": ufiles,
             "V": vfiles,
             "W": wfiles,
            }

variables = {"U": "uo",
             "V": "vo",
             "W": "wo",}

dimensions={'lon':'longitude',
            'lat':'latitude',
            'time':'time',
            'depth': "depth"}


## now the fieldset
fieldset = FieldSet.from_netcdf(
    filenames,
    variables,
    dimensions,
)

##check the error
def CheckError(particle, fieldset, time):
    if particle.state >= 50:  # This captures all Errors
        particle.delete()

## Time and depth initial conditios
release_date = np.datetime64(sys.argv[1])
time_origin=np.array(release_date,dtype='datetime64[ns]')
time = np.repeat(time_origin, num_particles)  # Assign the same time to all particles
depth = np.random.uniform(0,10, size=num_particles)  # Choose random depths

# initiate pset
pset = ParticleSet(
    fieldset=fieldset,
    lon = lon_start,
    lat = lat_start,
    depth=depth,
    time=time
) 

rnd=str(np.random.randint(1234))

out_path = '../data/tracks/' #path to store the particle zarr
out_fn = 'Parcels_run_'+ str(time_origin) + rnd

output_file = pset.ParticleFile(name=out_path+out_fn, 
                                outputdt=timedelta(hours=hours),
                               chunks = (num_particles,365))

## Execute particles
pset.execute(
    [AdvectionRK4_3D,CheckError],
    runtime=timedelta(days=days),
    dt=timedelta(minutes=minutes),
    output_file= output_file
)