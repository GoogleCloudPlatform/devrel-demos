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

# Create or delete a node pool in an episode cluster.
#
# Usage:
#   gke-nodepool.sh create --episode ep04 --pool c4-96 --machine-type c4-standard-96
#                          [--cluster NAME] [--nodes 1] [--spot] [--sandbox gvisor]
#                          [--system-config FILE] [--accelerator type=nvidia-l4,count=1]
#                          [--ttl 3d] [--] [extra gcloud flags]
#   gke-nodepool.sh delete --episode ep04 --pool c4-96 [--cluster NAME]
#   gke-nodepool.sh scale-to-zero --episode ep04 --pool c4-96 [--cluster NAME]
# Set DRY_RUN=1 to print the gcloud commands without running them.
set -euo pipefail
. "$(dirname "$0")/lib.sh"

action="${1:-}"; shift || true
episode=""; pool=""; cluster=""; machine=""; nodes=1; spot=0; sandbox=""; sysconfig=""; accel=""; ttl="3d"; extra=()
while [ $# -gt 0 ]; do
  case "$1" in
    --episode) episode="$2"; shift 2 ;;
    --pool) pool="$2"; shift 2 ;;
    --cluster) cluster="$2"; shift 2 ;;
    --machine-type) machine="$2"; shift 2 ;;
    --nodes) nodes="$2"; shift 2 ;;
    --spot) spot=1; shift ;;
    --sandbox) sandbox="$2"; shift 2 ;;
    --system-config) sysconfig="$2"; shift 2 ;;
    --accelerator) accel="$2"; shift 2 ;;
    --ttl) ttl="$2"; shift 2 ;;
    --) shift; extra=("$@"); break ;;
    *) die "unknown flag: $1" ;;
  esac
done

[ -n "$episode" ] && [ -n "$pool" ] || die "--episode and --pool are required"
require PROJECT_ID ZONE
cluster="${cluster:-${CLUSTER_PREFIX:-k8s-revisited}-${episode}}"
common=(--cluster "$cluster" --project "$PROJECT_ID" --location "$ZONE")

case "$action" in
  create)
    [ -n "$machine" ] || die "--machine-type is required"
    flags=(--machine-type "$machine" --num-nodes "$nodes" --labels "$(labels "$episode" "$ttl")")
    [ "$spot" = "1" ] && flags+=(--spot)
    [ -n "$sandbox" ] && flags+=(--sandbox "type=$sandbox")
    [ -n "$sysconfig" ] && flags+=(--system-config-from-file "$sysconfig")
    [ -n "$accel" ] && flags+=(--accelerator "$accel")
    run gcloud container node-pools create "$pool" "${common[@]}" "${flags[@]}" "${extra[@]}"
    ;;
  delete)
    run gcloud container node-pools delete "$pool" "${common[@]}" --quiet
    ;;
  scale-to-zero)
    run gcloud container clusters resize "$cluster" --node-pool "$pool" --num-nodes 0 \
      --project "$PROJECT_ID" --location "$ZONE" --quiet
    ;;
  *) die "usage: gke-nodepool.sh create|delete|scale-to-zero --episode epNN --pool NAME [...]" ;;
esac
