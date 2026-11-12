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

# Shared helpers for the infra scripts. Source it; don't run it.

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$LIB_DIR/.env" ]; then
  # shellcheck disable=SC1091
  set -a; . "$LIB_DIR/.env"; set +a
fi

DRY_RUN="${DRY_RUN:-0}"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() { log "error: $*"; exit 1; }

# run CMD...: prints the command; runs it unless DRY_RUN=1.
run() {
  printf '+ %s\n' "$*" >&2
  if [ "$DRY_RUN" = "1" ]; then return 0; fi
  "$@"
}

require() {
  local name
  for name in "$@"; do
    [ -n "${!name:-}" ] || die "$name is not set (see shared/infra/env.example)"
  done
}

# labels EPISODE TTL: the label string every resource gets.
labels() {
  local episode="${1:?episode}" ttl="${2:-3d}"
  printf 'series=k8s-revisited,episode=%s,ttl=%s' "$episode" "$ttl"
}
