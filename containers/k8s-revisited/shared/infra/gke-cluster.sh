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

# Create or delete a zonal GKE cluster for one episode.
#
# Usage:
#   gke-cluster.sh create --episode ep02 [--name NAME] [--channel rapid] [--version VERSION]
#                         [--autopilot] [--ttl 3d] [--] [extra gcloud flags]
#   gke-cluster.sh delete --episode ep02 [--name NAME]
# Set DRY_RUN=1 to print the gcloud commands without running them.
set -euo pipefail
. "$(dirname "$0")/lib.sh"

action="${1:-}"; shift || true
episode=""; name=""; channel="rapid"; version=""; autopilot=0; ttl="3d"; extra=()
while [ $# -gt 0 ]; do
  case "$1" in
    --episode) episode="$2"; shift 2 ;;
    --name) name="$2"; shift 2 ;;
    --channel) channel="$2"; shift 2 ;;
    --version) version="$2"; shift 2 ;;
    --autopilot) autopilot=1; shift ;;
    --ttl) ttl="$2"; shift 2 ;;
    --) shift; extra=("$@"); break ;;
    *) die "unknown flag: $1" ;;
  esac
done

[ -n "$episode" ] || die "--episode is required"
require PROJECT_ID ZONE REGION
name="${name:-${CLUSTER_PREFIX:-k8s-revisited}-${episode}}"

case "$action" in
  create)
    if [ "$autopilot" = "1" ]; then
      run gcloud container clusters create-auto "$name" --project "$PROJECT_ID" --location "$REGION" \
        --release-channel "$channel" --labels "$(labels "$episode" "$ttl")" ${version:+--cluster-version "$version"} "${extra[@]}"
    else
      run gcloud container clusters create "$name" --project "$PROJECT_ID" --location "$ZONE" \
        --release-channel "$channel" ${version:+--cluster-version "$version"} \
        --num-nodes 1 --machine-type e2-standard-4 \
        --labels "$(labels "$episode" "$ttl")" "${extra[@]}"
    fi
    run gcloud container clusters get-credentials "$name" --project "$PROJECT_ID" \
      --location "$([ "$autopilot" = "1" ] && echo "$REGION" || echo "$ZONE")"
    ;;
  delete)
    if [ "$DRY_RUN" = "1" ]; then
      # Dry runs make no API calls, so they can't tell a zonal cluster from a regional one.
      run gcloud container clusters delete "$name" --project "$PROJECT_ID" --location "$ZONE-or-$REGION" --quiet
      exit 0
    fi
    # Find the cluster: Standard clusters are zonal, Autopilot clusters are regional.
    # A cluster that exists in neither place is already gone, which is fine for teardown.
    loc=""
    for l in "$ZONE" "$REGION"; do
      if out="$(gcloud container clusters describe "$name" --project "$PROJECT_ID" --location "$l" --format 'value(name)' 2>&1)"; then
        loc="$l"; break
      fi
      case "$out" in
        *NOT_FOUND*|*"code=404"*|*"Not found"*|*"not found"*) ;;
        *) die "could not look up $name in $l: $out" ;;
      esac
    done
    if [ -z "$loc" ]; then
      log "$name doesn't exist in $ZONE or $REGION; nothing to delete"
      exit 0
    fi
    # GKE refuses to delete a cluster while another operation runs on it (an Autopilot
    # cluster often has an upgrade or node change in flight). Wait for those and retry;
    # fail right away on any other error.
    retry_sleep="${RETRY_SLEEP:-60}"
    for attempt in 1 2 3 4 5 6; do
      for op in $(gcloud container operations list --project "$PROJECT_ID" --location "$loc" \
          --filter "status=RUNNING AND targetLink~/clusters/${name}(/|$)" --format 'value(name)'); do
        log "waiting for operation $op on $name"
        run gcloud container operations wait "$op" --project "$PROJECT_ID" --location "$loc" || true
      done
      printf '+ gcloud container clusters delete %s --project %s --location %s --quiet\n' "$name" "$PROJECT_ID" "$loc" >&2
      if out="$(gcloud container clusters delete "$name" --project "$PROJECT_ID" --location "$loc" --quiet 2>&1)"; then
        printf '%s\n' "$out" >&2
        exit 0
      fi
      printf '%s\n' "$out" >&2
      case "$out" in
        *"incompatible operation"*|*"operation is in progress"*) ;;
        *) die "could not delete $name" ;;
      esac
      log "another operation is running on $name (attempt $attempt of 6); retrying in ${retry_sleep}s"
      sleep "$retry_sleep"
    done
    die "could not delete $name; check: gcloud container operations list --project $PROJECT_ID --location $loc"
    ;;
  *) die "usage: gke-cluster.sh create|delete --episode epNN [...]" ;;
esac
