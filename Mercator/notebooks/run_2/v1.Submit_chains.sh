#!/bin/bash
# Submits every "sbatch v1.Run_parcels_UVW.sh <first> <last> <seed>" line of a list file (default: the
# readme) as N  dependency chains (default 4): in each chain a job starts only after the previous one
# has ended (afterany: also after a failure or timeout, so one bad notebook does not block the chain).
# At most N jobs run at the same time, counting the jobs you already have in the queue: the first job
# of each chain waits for one of them.
#
# Skipped:  lines starting with '#', jobs whose releases are all done (v1.check_done.py: executed
#           notebook complete + zarr exists), jobs with the same name already in the queue.
# Partly done jobs: only the missing offsets are submitted, with v3.Rerun_offset.sh.
#
# Run on the login node, from run_2:
#   bash v1.Submit_chains.sh readme_Parcels_Release.m 4 dry    # only print what would be submitted
#   bash v1.Submit_chains.sh                                   # submit (readme, 4 chains)
list=${1:-readme_Parcels_Release.m}
nchains=${2:-4}
dry=${3:-}
py=/work/bk1450/b383184/conda/envs/parcels_3.1.2/bin/python

mapfile -t jobs < <(grep -E '^sbatch v1\.Run_parcels_UVW\.sh +[0-9]+ +[0-9]+ +[0-9]+' "$list" | awk '{print $3, $4, $5}')
mapfile -t queued < <(squeue -u "$USER" -h -o '%i %j')
echo "${#jobs[@]} job lines in ${list}; ${#queued[@]} jobs of yours already in the queue: ${queued[*]}"

# the first job of each chain waits for the already queued jobs (spread over the chains)
declare -a last
for k in "${!queued[@]}"; do
  c=$((k % nchains)); id=${queued[$k]%% *}
  last[$c]=${last[$c]:+${last[$c]}:}${id}
done

n=0
for line in "${jobs[@]}"; do
  read -r first lastoff seed <<< "$line"
  name="MER_v3_${seed}_${first}"
  if printf '%s\n' "${queued[@]}" | grep -q " ${name}$"; then
    echo "skip ${first}-${lastoff} seed ${seed}: already in the queue"; continue
  fi
  todo=($($py v1.check_done.py "$first" "$lastoff" "$seed"))
  total=$(( (lastoff - first) / 5 + 1 ))
  if [ ${#todo[@]} -eq 0 ]; then
    echo "skip ${first}-${lastoff} seed ${seed}: all ${total} done or running"; continue
  elif [ ${#todo[@]} -eq $total ]; then
    cmd=(v1.Run_parcels_UVW.sh "$first" "$lastoff" "$seed")
  else
    cmd=(v3.Rerun_offset.sh "$seed" "${todo[@]}")
    echo "partly done ${first}-${lastoff} seed ${seed}: ${#todo[@]} of ${total} missing -> rerun only those"
  fi
  c=$((n % nchains)); n=$((n + 1))
  dep=${last[$c]:+--dependency=afterany:${last[$c]}}
  if [ -n "$dry" ]; then
    id="chain${c}_${first}"
    echo "sbatch --parsable --job-name=${name} ${dep} ${cmd[*]}"
  else
    id=$(sbatch --parsable --job-name="${name}" ${dep} "${cmd[@]}") || { echo "sbatch failed at ${first}-${lastoff}"; exit 1; }
    echo "chain ${c}: job ${id}  offsets ${first}-${lastoff}  seed ${seed}  ${dep}"
  fi
  last[$c]=$id
done
echo "${n} jobs $([ -n "$dry" ] && echo 'would be ')submitted"
