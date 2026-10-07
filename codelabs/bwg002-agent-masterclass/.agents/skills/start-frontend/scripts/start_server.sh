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

# ==============================================================================
# Script: start_server.sh
# Description: Frees port 8080 if occupied, loads Cloud environment via setenv.sh,
#              and starts the Pitch Generator web server.
# Usage: ./start_server.sh [--check-only | --stop-only | --port <port>]
# ==============================================================================

set -euo pipefail

PORT="${PORT:-8080}"
ACTION="start"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT="$2"
      shift 2
      ;;
    --check-only)
      ACTION="check"
      shift
      ;;
    --stop-only)
      ACTION="stop"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$REPO_ROOT"

free_port() {
  local target_port="$1"
  local pids
  pids=$(lsof -tiTCP:"${target_port}" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -z "${pids}" ]]; then
    pids=$(lsof -ti ":${target_port}" 2>/dev/null || true)
  fi
  if [[ -n "${pids}" ]]; then
    echo "[start-frontend] Port ${target_port} is occupied by PID(s): ${pids}."
    echo "[start-frontend] Terminating existing process(es)..."
    for pid in ${pids}; do
      kill "${pid}" 2>/dev/null || true
    done
    sleep 1
    local remaining
    remaining=$(lsof -tiTCP:"${target_port}" -sTCP:LISTEN 2>/dev/null || true)
    if [[ -n "${remaining}" ]]; then
      echo "[start-frontend] Force killing remaining PID(s): ${remaining}..."
      for pid in ${remaining}; do
        kill -9 "${pid}" 2>/dev/null || true
      done
      sleep 1
    fi
    local final_check
    final_check=$(lsof -tiTCP:"${target_port}" -sTCP:LISTEN 2>/dev/null || true)
    if [[ -z "${final_check}" ]]; then
      echo "[start-frontend] Port ${target_port} successfully freed."
    else
      echo "[start-frontend] Warning: PID(s) ${final_check} could not be terminated directly."
    fi
  else
    echo "[start-frontend] Port ${target_port} is already free."
  fi
}

case "${ACTION}" in
  check)
    pids=$(lsof -tiTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null || true)
    if [[ -n "${pids}" ]]; then
      echo "[start-frontend] Port ${PORT} is occupied by PID(s): ${pids}."
      exit 1
    else
      echo "[start-frontend] Port ${PORT} is free."
      exit 0
    fi
    ;;
  stop)
    free_port "${PORT}"
    exit 0
    ;;
  start)
    free_port "${PORT}"
    if [[ -f "${REPO_ROOT}/setenv.sh" ]]; then
      # shellcheck disable=SC1091
      source "${REPO_ROOT}/setenv.sh"
    fi
    echo "[start-frontend] Starting Pitch Generator server on port ${PORT}..."
    export PORT="${PORT}"
    exec python3 pitch_generator/fast_api_app.py
    ;;
esac
