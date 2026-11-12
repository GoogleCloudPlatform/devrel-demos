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

# Run the Ep1 core experiments against one or more GKE clusters (kubectl contexts).
#
# Usage: bench/compare-channels.sh CONTEXT [CONTEXT...]
# Writes, under results/ (gitignored, so measurements stay with you):
#   env-<context>.json                 versions, nodes, kernel and runtime for each cluster
#   census.md, census-<context>.json   served APIs, named capabilities, RuntimeClasses, feature gates
#   knobs.md, knobs.json, knobs.err    effective kubelet config and kubelet feature gates per node pool
#   diff-2020-<context>.md             each cluster next to the hand-written 2020 baseline
#   five-things.csv                    the five demos on each cluster, with a functional check each
#   five-things-errors.log             full error messages and Pod events behind any failed demo
#
# An Autopilot cluster has no nodes until a workload asks for one, so a cluster with
# no nodes gets a small "keepalive" Pod first and keeps it until the census is done.
set -euo pipefail
cd "$(dirname "$0")/.."
[ $# -ge 1 ] || { echo "usage: $0 CONTEXT [CONTEXT...]" >&2; exit 2; }

mkdir -p results/bin
go build -o results/bin/census ./src/census

warmed=()
cleanup() {
  for c in "${warmed[@]}"; do
    kubectl --context "$c" delete pod census-keepalive --wait=false >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT

for c in "$@"; do
  if [ -z "$(kubectl --context "$c" get nodes -o name 2>/dev/null)" ]; then
    echo "no nodes on $c yet: starting a keepalive Pod so the census can read one" >&2
    kubectl --context "$c" run census-keepalive --image=busybox:1.37 --restart=Never \
      --labels=k8s-revisited/demo=keepalive -- sleep 7200 >/dev/null
    warmed+=("$c")
  fi
done
for c in "${warmed[@]}"; do
  kubectl --context "$c" wait --for=condition=Ready pod/census-keepalive --timeout=900s >/dev/null ||
    echo "warning: no Ready node on $c after 15 minutes; census will have no node data there" >&2
done

ctx_flags=()
for c in "$@"; do ctx_flags+=(--context "$c"); done

# The run environment (versions, nodes, kernel, runtime) for every cluster, not just one.
for c in "$@"; do
  safe="$(printf '%s' "$c" | sed 's/[^A-Za-z0-9._-]\{1,\}/-/g')"
  PYTHONPATH=../shared/bench python3 -m k8s_revisited_bench.envinfo --context "$c" --out "results/env-${safe}.json" >/dev/null
done

results/bin/census "${ctx_flags[@]}" --out-dir results > results/census.md
results/bin/census knobs "${ctx_flags[@]}" > results/knobs.md 2> results/knobs.err
results/bin/census knobs "${ctx_flags[@]}" --format json > results/knobs.json 2>/dev/null

for c in "$@"; do
  safe="$(printf '%s' "$c" | sed 's/[^A-Za-z0-9._-]\{1,\}/-/g')"
  results/bin/census diff baseline/k8s-2020.json "results/census-${safe}.json" > "results/diff-2020-${safe}.md"
done

echo "context,demo,dry_run,applied,check,note" > results/five-things.csv
: > results/five-things-errors.log
for c in "$@"; do
  echo "five demos on $c" >&2
  ./bench/five_things.sh "$c" >> results/five-things.csv
done

echo "wrote results/census.md results/knobs.md results/diff-2020-*.md results/five-things.csv"
