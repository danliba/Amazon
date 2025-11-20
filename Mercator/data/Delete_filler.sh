outpath='/work/bk1450/b383184/Amazon/Mercator/data/variables_c/'
# inpath='/work/bk1450/b383184/Amazon/Mercator/data/variables/'

mkdir -p "$outpath"
cd '/work/bk1450/b383184/Amazon/Mercator/data/variables/'

for file in U_200*.nc; do
    filename=$(basename "$file")
    output="${outpath}${filename%.nc}c.nc"
    cdo setmissval,nan "$file" "$output"
    echo "Processed: $file"

done

wait
# V
for file in V_200*.nc; do
    filename=$(basename "$file")
    output="${outpath}${filename%.nc}c.nc"
    cdo setmissval,nan "$file" "$output"
    echo "Processed: $file"

done

wait
##W
for file in W_200*.nc; do
    filename=$(basename "$file")
    output="${outpath}${filename%.nc}c.nc"
    cdo setmissval,nan "$file" "$output"
    echo "Processed: $file"

done
wait

##T
for file in T_200*.nc; do
    filename=$(basename "$file")
    output="${outpath}${filename%.nc}c.nc"
    cdo setmissval,nan "$file" "$output"
    echo "Processed: $file"

done
wait

##S
for file in S_200*.nc; do
    filename=$(basename "$file")
    output="${outpath}${filename%.nc}c.nc"
    cdo setmissval,nan "$file" "$output"
    echo "Processed: $file"

done
wait