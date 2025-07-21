#!/bin/bash

dates=$(seq 6 12)  # June to December
max_jobs=4         # Maximum concurrent jobs

for m in $dates; do
    date_str="2022-$(printf "%02d" $m)-01"
    echo "Submitting for $date_str"
    sbatch run_particles.sh $date_str

    # Wait if number of running jobs for this user >= max_jobs
    while [ $(squeue -u $USER -h | wc -l) -ge $max_jobs ]; do
        echo "Waiting... $(date)"
        sleep 10
    done
done
