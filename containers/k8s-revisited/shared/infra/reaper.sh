#!/usr/bin/env bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Find (and optionally delete) anything labeled series=k8s-revisited.
#
# Usage:
#   reaper.sh --check    list labeled resources; exit 1 if any exist
#   reaper.sh --delete   delete them after confirmation
set -euo pipefail
. "$(dirname "$0")/lib.sh"

mode="${1:---check}"
require PROJECT_ID
filter='resourceLabels.series=k8s-revisited'

clusters=$(gcloud container clusters list --project "$PROJECT_ID" --filter "$filter" \
  --format 'value(name,location)' 2>/dev/null || true)
instances=$(gcloud compute instances list --project "$PROJECT_ID" --filter 'labels.series=k8s-revisited' \
  --format 'value(name,zone.basename())' 2>/dev/null || true)
disks=$(gcloud compute disks list --project "$PROJECT_ID" --filter 'labels.series=k8s-revisited' \
  --format 'value(name,zone.basename())' 2>/dev/null || true)
buckets=$(gcloud storage buckets list --project "$PROJECT_ID" --filter 'labels.series=k8s-revisited' \
  --format 'value(name)' 2>/dev/null || true)

found=0
report() {
  local kind="$1" list="$2"
  if [ -n "$list" ]; then
    found=1
    printf '%s:\n' "$kind"
    printf '  %s\n' "$list"
  fi
}
report clusters "$clusters"
report instances "$instances"
report disks "$disks"
report buckets "$buckets"

if [ "$found" = "0" ]; then
  echo "reaper: nothing labeled series=k8s-revisited in $PROJECT_ID"
  exit 0
fi

if [ "$mode" = "--check" ]; then
  echo "reaper: labeled resources still exist"
  exit 1
fi

[ "$mode" = "--delete" ] || die "usage: reaper.sh --check|--delete"
read -r -p "Delete everything listed above? [y/N] " answer
[ "$answer" = "y" ] || { echo "aborted"; exit 1; }
while read -r name loc; do [ -n "$name" ] && run gcloud container clusters delete "$name" --location "$loc" --project "$PROJECT_ID" --quiet; done <<< "$clusters"
while read -r name zone; do [ -n "$name" ] && run gcloud compute instances delete "$name" --zone "$zone" --project "$PROJECT_ID" --quiet; done <<< "$instances"
while read -r name zone; do [ -n "$name" ] && run gcloud compute disks delete "$name" --zone "$zone" --project "$PROJECT_ID" --quiet; done <<< "$disks"
while read -r name; do [ -n "$name" ] && run gcloud storage rm --recursive "gs://$name"; done <<< "$buckets"
