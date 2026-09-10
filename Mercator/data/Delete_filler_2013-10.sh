#!/bin/bash
# Strip the 9.96921e+36 fill value from the raw 2013-10 files.
#
# U,V land in variables_c/UVW/ and T,S in variables_c/tracers/ -- that is where
# the rest of the pipeline reads them from.
#
# W is deliberately absent: Fix_W.ipynb reads the RAW variables/W_*.nc and writes
# W_*fc.nc into UVW/ itself, so W never goes through cdo.

module load cdo 2>/dev/null || module load cdo/2.5.3-gcc-11.2.0

inpath='/work/bk1450/b383184/Amazon/Mercator/data/variables'
uvw_out='/work/bk1450/b383184/Amazon/Mercator/data/variables_c/UVW'
trc_out='/work/bk1450/b383184/Amazon/Mercator/data/variables_c/tracers'

ym='2013-10'

mkdir -p "$uvw_out" "$trc_out"

strip_fill() {
  var=$1
  outdir=$2
  in="${inpath}/${var}_${ym}.nc"
  out="${outdir}/${var}_${ym}c.nc"

  if [[ ! -f "$in" ]]; then
    echo "MISSING input: $in -- skipping ${var}"
    return 1
  fi
  if [[ -f "$out" ]]; then
    echo "Exists, skipping: $out"
    return 0
  fi

  echo "Processing ${var}_${ym} -> ${out}"
  cdo setmissval,nan "$in" "$out" || { echo "FAILED cdo on $in"; return 1; }
}

strip_fill U "$uvw_out"
strip_fill V "$uvw_out"
strip_fill T "$trc_out"
strip_fill S "$trc_out"

echo
echo "=== result ==="
ls -la "${uvw_out}/U_${ym}c.nc" "${uvw_out}/V_${ym}c.nc" \
       "${trc_out}/T_${ym}c.nc" "${trc_out}/S_${ym}c.nc" 2>&1
