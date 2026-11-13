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

# Run the five "what you missed" demos on one cluster and check that each one
# does what it claims, not only that the Pod starts.
#
# Usage: bench/five_things.sh CONTEXT >> results/five-things.csv
# Prints CSV rows: context,demo,dry_run,applied,check,note
# Full error messages and Pod events go to ERR_LOG (default results/five-things-errors.log).
# READY_TIMEOUT (seconds, default 600) covers node provisioning on Autopilot.
set -uo pipefail
cd "$(dirname "$0")/.."

ctx="${1:?usage: five_things.sh CONTEXT}"
timeout="${READY_TIMEOUT:-600}"
ERR_LOG="${ERR_LOG:-results/five-things-errors.log}"
mkdir -p "$(dirname "$ERR_LOG")"
current_demo=""

k() { kubectl --context "$ctx" "$@"; }
row() { printf '%s,%s,%s,%s,%s,%s\n' "$ctx" "$1" "$2" "$3" "$4" "$(printf '%s' "$5" | tr ',\n' '; ')"; }
# short TEXT: logs TEXT in full to ERR_LOG, then prints it as one line for the CSV note
# column: Warning lines dropped, at most 1000 characters.
short() {
  printf '== %s %s\n%s\n\n' "$ctx" "$current_demo" "$1" >> "$ERR_LOG"
  printf '%s' "$1" | sed '/^Warning:/d' | tr '\n' ' ' | cut -c1-1000
}
# pod_events LABEL: the latest events for the demo's Pod, for notes on Pods that never became Ready.
pod_events() {
  local p
  p="$(k get pod -l "k8s-revisited/demo=$1" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)"
  [ -n "$p" ] || return 0
  k get events --field-selector "involvedObject.name=$p" --sort-by=.lastTimestamp \
    -o custom-columns=REASON:.reason,MESSAGE:.message --no-headers 2>/dev/null | tail -n 3
}

# wait_ready LABEL: wait until a Pod with this demo label exists and is Ready; print its name.
wait_ready() {
  local label="$1" deadline=$((SECONDS + timeout)) pod=""
  while [ "$SECONDS" -lt "$deadline" ]; do
    pod="$(k get pod -l "k8s-revisited/demo=$label" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
    if [ -n "$pod" ]; then
      k wait --for=condition=Ready "pod/$pod" --timeout="$((deadline - SECONDS))s" >/dev/null 2>&1 && { echo "$pod"; return 0; }
      return 1
    fi
    sleep 3
  done
  return 1
}

check_sidecar() {
  local started
  started="$(k get pod "$1" -o jsonpath='{.status.initContainerStatuses[0].started}')"
  [ "$started" = "true" ] && echo "pass|sidecar started before the app and is still running" || echo "fail|sidecar not running"
}

check_resize() {
  local pod="$1" got restarts deadline err
  if ! err="$(k patch pod "$pod" --subresource resize --patch \
      '{"spec":{"containers":[{"name":"app","resources":{"requests":{"cpu":"500m"},"limits":{"cpu":"1"}}}]}}' 2>&1 >/dev/null)"; then
    echo "fail|the resize subresource rejected the patch: $(short "$err")"; return
  fi
  deadline=$((SECONDS + 90))
  while [ "$SECONDS" -lt "$deadline" ]; do
    got="$(k get pod "$pod" -o jsonpath='{.status.containerStatuses[0].resources.requests.cpu}')"
    restarts="$(k get pod "$pod" -o jsonpath='{.status.containerStatuses[0].restartCount}')"
    if [ "$got" = "500m" ]; then
      [ "$restarts" = "0" ] && echo "pass|CPU request changed without a container restart" || echo "fail|the container restarted"
      return
    fi
    sleep 3
  done
  echo "fail|the new CPU request never showed up in the Pod status"
}

check_image_volume() {
  local files
  files="$(k exec "$1" -- ls /models 2>/dev/null)"
  [ -n "$files" ] && echo "pass|the OCI artifact is mounted read-only at /models" || echo "fail|/models is empty or not mounted"
}

check_userns() {
  local map
  map="$(k exec "$1" -- cat /proc/self/uid_map 2>/dev/null | awk 'NR == 1 {print $1, $2, $3}')"
  case "$map" in
    "") echo "fail|could not read /proc/self/uid_map" ;;
    "0 0 4294967295") echo "fail|identity mapping: no user namespace" ;;
    *) echo "pass|root in the container maps to host UID ${map#0 }" ;;
  esac
}

# The swap demo runs only where a node pool named "swap" exists (GKE Standard with
# swap in its node system config). swap-demo lands on that pool and allocates past
# its memory limit; swap-contrast is the same container on a pool without swap.
run_swap() {
  current_demo=swap
  local f=manifests/five-things/swap.yaml dry=fail applied=no check note pod phase reason node used
  if [ -z "$(k get nodes -l cloud.google.com/gke-nodepool=swap -o name 2>/dev/null)" ]; then
    row swap skipped skipped skipped "no node pool with swap on this cluster"
    return
  fi
  k apply --dry-run=server -f "$f" >/dev/null 2>&1 && dry=pass
  if [ "$dry" = "pass" ] && k apply -f "$f" >/dev/null 2>&1; then
    applied=yes
    sleep 45
    phase="$(k get pod swap-demo -o jsonpath='{.status.phase}' 2>/dev/null)"
    node="$(k get pod swap-demo -o jsonpath='{.spec.nodeName}' 2>/dev/null)"
    # The kubelet Summary API reports node swap use as node.swap.swapUsageBytes.
    used="$(k get --raw "/api/v1/nodes/$node/proxy/stats/summary" 2>/dev/null |
      python3 -c 'import json,sys; print(json.load(sys.stdin).get("node", {}).get("swap", {}).get("swapUsageBytes", ""))' 2>/dev/null)"
    reason="$(k get pod swap-contrast -o jsonpath='{.status.containerStatuses[0].state.terminated.reason}' 2>/dev/null)"
    if [ "$phase" = "Running" ] && [ "$reason" = "OOMKilled" ]; then
      check=pass; note="past its memory limit: kept running on the swap pool; OOMKilled on the pool without swap"
    else
      check=fail; note="swap pool phase=${phase:-unknown}; no-swap pool reason=${reason:-none}"
    fi
    [ -n "$used" ] && note="$note; node reports swap in use: $([ "$used" != "0" ] && echo yes || echo no)"
  else
    check=skipped; note="server-side dry-run or apply failed"
  fi
  row swap "$dry" "$applied" "$check" "$note"
  k delete -f "$f" --wait=false >/dev/null 2>&1 || true
}

for demo in sidecar resize image-volume userns; do
  current_demo="$demo"
  f="manifests/five-things/$demo.yaml"
  dry=fail; applied=no; check=skipped; note=""
  if k apply --dry-run=server -f "$f" >/dev/null 2>&1; then
    dry=pass
    if k apply -f "$f" >/dev/null 2>&1; then
      applied=yes
      if pod="$(wait_ready "$demo")"; then
        result="$(check_"${demo//-/_}" "$pod")"
        check="${result%%|*}"; note="${result#*|}"
      else
        check=fail
        note="the Pod never became Ready: $(k get pod -l "k8s-revisited/demo=$demo" -o jsonpath='{.items[0].status.containerStatuses[0].state.waiting.reason}' 2>/dev/null); events: $(short "$(pod_events "$demo")")"
      fi
    else
      note="apply failed: $(short "$(k apply -f "$f" 2>&1)")"
    fi
  else
    note="$(short "$(k apply --dry-run=server -f "$f" 2>&1)")"
  fi
  row "$demo" "$dry" "$applied" "$check" "$note"
  k delete -f "$f" --wait=false >/dev/null 2>&1 || true
done

run_swap
