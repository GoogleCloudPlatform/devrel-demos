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
# Description: Frees port 8080 (and port 8801 when --with-visual-director is set),
#              loads .env, and starts the Pitch Generator web server (and optional
#              standalone Visual Director A2A service).
# Usage: ./start_server.sh [--check-only | --stop-only | --port <port> | --with-visual-director | --visual-director-only]
# ==============================================================================

set -euo pipefail

PORT="${PORT:-8080}"
VD_PORT="${VD_PORT:-8801}"
ACTION="start"
WITH_VISUAL_DIRECTOR=0
VISUAL_DIRECTOR_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT="$2"
      shift 2
      ;;
    --vd-port)
      VD_PORT="$2"
      shift 2
      ;;
    --with-visual-director)
      WITH_VISUAL_DIRECTOR=1
      shift
      ;;
    --visual-director-only)
      VISUAL_DIRECTOR_ONLY=1
      shift
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

load_env() {
  if [[ -f "${REPO_ROOT}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.env"
    set +a
  fi
  export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
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
    if [[ "${WITH_VISUAL_DIRECTOR}" -eq 1 || "${VISUAL_DIRECTOR_ONLY}" -eq 1 ]]; then
      free_port "${VD_PORT}"
    fi
    free_port "${PORT}"
    exit 0
    ;;
  start)
    load_env
    if [[ "${VISUAL_DIRECTOR_ONLY}" -eq 1 ]]; then
      free_port "${VD_PORT}"
      echo "[start-frontend] Starting Visual Director A2A service on port ${VD_PORT}..."
      export PORT="${VD_PORT}"
      export SERVICE_ROLE="visual-director"
      exec python3 -m pitch_generator.fast_api_app
    fi

    if [[ "${WITH_VISUAL_DIRECTOR}" -eq 1 ]]; then
      free_port "${VD_PORT}"
      echo "[start-frontend] Starting Visual Director A2A service on port ${VD_PORT}..."
      PORT="${VD_PORT}" SERVICE_ROLE="visual-director" python3 -m pitch_generator.fast_api_app &
      export VISUAL_DIRECTOR_URL="http://127.0.0.1:${VD_PORT}"
      sleep 1
    fi

    free_port "${PORT}"
    echo "[start-frontend] Starting Pitch Generator server on port ${PORT}..."
    export PORT="${PORT}"
    export SERVICE_ROLE="pitch-generator"
    exec python3 -m pitch_generator.fast_api_app
    ;;
esac
