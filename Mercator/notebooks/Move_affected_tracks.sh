#!/bin/bash
# Move the zarr stores listed in data/affected_tracks.txt out of the way before
# re-running them (parcels will not cleanly overwrite an existing store).
# They land in data/tracks_badW/<seed>/ so nothing is destroyed; delete that
# folder once the re-runs are verified.
set -e pipefail

DATA="/work/bk1450/b383184/Amazon/Mercator/data"
LIST="${DATA}/affected_tracks.txt"
BACKUP="${DATA}/tracks_badW"

moved=0
missing=0
while IFS= read -r rel; do
  [[ -z "$rel" ]] && continue
  src="${DATA}/${rel}"
  seed=$(dirname "$rel"); seed=${seed#tracks_}
  dst="${BACKUP}/${seed}"
  if [[ -d "$src" ]]; then
    mkdir -p "$dst"
    mv "$src" "$dst/"
    moved=$((moved+1))
  else
    echo "not found (already moved?): $rel"
    missing=$((missing+1))
  fi
done < "$LIST"

echo "moved ${moved} stores to ${BACKUP} (${missing} not found)"
