#!/bin/bash
#
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -o errexit
set -o nounset
set -o pipefail

ERR_GENERIC=1
ERR_COMMAND_NOT_AVAILABLE=2
ERR_LIBRARY_NOT_AVAILABLE=3

is_command_available() {
  if command -v "${1}" >/dev/null 2>&1; then
    return 0
  else
    return "${ERR_COMMAND_NOT_AVAILABLE}"
  fi
}

if ! is_command_available git; then
  echo "Git is not available on the host. Install it and run this script again"
  exit "${ERR_COMMAND_NOT_AVAILABLE}"
fi

if ! is_command_available terraform; then
  echo "Terraform is not available on the host. Install it and run this script again"
  exit "${ERR_COMMAND_NOT_AVAILABLE}"
fi

core_platform_terraservices=(
  "initialize"
  "networking"
  "container_cluster"
)

export TF_IN_AUTOMATION="1"

ACCELERATED_PLATFORMS_REPOSITORY_PATH="${REPOSITORY_ROOT_DIRECTORY_PATH}/accelerated-platforms"
export ACP_REPO_DIR="${ACCELERATED_PLATFORMS_REPOSITORY_PATH}"
export ACP_PLATFORM_BASE_DIR="${ACCELERATED_PLATFORMS_REPOSITORY_PATH}/platforms/gke/base"
export ACP_PLATFORM_CORE_DIR="${ACP_PLATFORM_BASE_DIR}/core"

export TF_VAR_cluster_project_id="${GOOGLE_CLOUD_PROJECT_ID}"
export TF_VAR_platform_name="a-g-demo"
export TF_VAR_terraform_project_id="${TF_VAR_cluster_project_id}"
