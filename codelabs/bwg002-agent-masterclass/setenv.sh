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

# /**
#  * @file setenv.sh
#  * @description Environment variable initializer for the Agentic Pitch Generator.
#  *
#  * Why: Centralizes environment resolution for both local development in the Antigravity 2.0 VM
#  * and Cloud Run deployments. It persists PROJECT_ID and REGION into .env when running live
#  * so reconnecting terminal sessions and Python processes recover state automatically, and
#  * exports GOOGLE_GENAI_USE_ENTERPRISE for the Gemini Enterprise Agent Platform.
#  *
#  * @param PROJECT_ID Optional environment override for the Google Cloud project ID.
#  * @param REGION Optional environment override for the Google Cloud region.
#  * @return 0 on successful environment configuration.
#  */

# /**
#  * Resolves and exports all required runtime environment variables for the Pitch Generator.
#  *
#  * Why: Checking local .env and ~/.env before querying gcloud allows offline test suites
#  * and reconnected VM terminals to restore configuration instantaneously without blocking
#  * on external metadata server calls.
#  *
#  * @return 0 after exporting variables and writing .env.
#  */
configure_pitch_env() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local env_file="${script_dir}/.env"
  local home_env_file="${HOME:-/tmp}/.env"

  if [[ -z "${PROJECT_ID:-}" || -z "${REGION:-}" ]]; then
    if [[ -f "${env_file}" ]]; then
      # shellcheck disable=SC1090
      source "${env_file}"
    elif [[ -f "${home_env_file}" ]]; then
      # shellcheck disable=SC1090
      source "${home_env_file}"
    fi
  fi

  if [[ -z "${PROJECT_ID:-}" ]]; then
    if [[ "${PITCH_OFFLINE_MODE:-0}" != "1" ]] && command -v gcloud >/dev/null 2>&1; then
      PROJECT_ID="$(gcloud config get-value project 2>/dev/null || true)"
      if [[ "${PROJECT_ID}" == "(unset)" ]]; then
        PROJECT_ID=""
      fi
    fi
    PROJECT_ID="${PROJECT_ID:-pitch-generator-dev}"
  fi

  if [[ -z "${REGION:-}" ]]; then
    if [[ "${PITCH_OFFLINE_MODE:-0}" != "1" ]] && command -v gcloud >/dev/null 2>&1; then
      REGION="$(gcloud config get-value compute/region 2>/dev/null || true)"
      if [[ "${REGION}" == "(unset)" ]]; then
        REGION=""
      fi
    fi
    REGION="${REGION:-us-central1}"
  fi

  export PROJECT_ID
  export REGION
  export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"
  export GOOGLE_CLOUD_REGION="${REGION}"
  export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-global}"
  export GOOGLE_GENAI_USE_ENTERPRISE="TRUE"
  export LOGS_BUCKET_NAME="${LOGS_BUCKET_NAME:-${PROJECT_ID}-bwg}"
  export MEMORY_BANK_ID="${MEMORY_BANK_ID:-pitch-memory-bank}"
  export VISUAL_DIRECTOR_URL="${VISUAL_DIRECTOR_URL:-http://localhost:8801}"
  export PITCH_GENERATOR_URL="${PITCH_GENERATOR_URL:-http://localhost:8080}"
  export FLASH_MODEL="${FLASH_MODEL:-gemini-3.8-flash}"
  export IMAGE_MODEL="${IMAGE_MODEL:-gemini-nano-banana-2.1}"

  local should_write_env="${PITCH_WRITE_ENV_FILE:-}"
  if [[ -z "${should_write_env}" ]]; then
    if [[ "${PITCH_OFFLINE_MODE:-0}" != "1" ]] && [[ "${PROJECT_ID}" != "pitch-generator-dev" ]]; then
      should_write_env="1"
    else
      should_write_env="0"
    fi
  fi

  if [[ "${should_write_env}" == "1" ]] && [[ -w "${script_dir}" ]]; then
    cat > "${env_file}" <<EOF
PROJECT_ID=${PROJECT_ID}
REGION=${REGION}
GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
GOOGLE_CLOUD_REGION=${GOOGLE_CLOUD_REGION}
GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION}
GOOGLE_GENAI_USE_ENTERPRISE=${GOOGLE_GENAI_USE_ENTERPRISE}
LOGS_BUCKET_NAME=${LOGS_BUCKET_NAME}
MEMORY_BANK_ID=${MEMORY_BANK_ID}
VISUAL_DIRECTOR_URL=${VISUAL_DIRECTOR_URL}
PITCH_GENERATOR_URL=${PITCH_GENERATOR_URL}
FLASH_MODEL=${FLASH_MODEL}
IMAGE_MODEL=${IMAGE_MODEL}
EOF
  fi

  echo "Configured Pitch Generator environment: PROJECT_ID=${GOOGLE_CLOUD_PROJECT}, REGION=${GOOGLE_CLOUD_REGION}, LOCATION=${GOOGLE_CLOUD_LOCATION}, BUCKET=${LOGS_BUCKET_NAME}"
  return 0
}

configure_pitch_env "$@"
