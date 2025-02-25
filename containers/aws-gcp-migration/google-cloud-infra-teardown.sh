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

PATH_TO_THIS_SCRIPT="${0}"
SCRIPT_DIRECTORY="$(dirname "${0}")"
REPOSITORY_ROOT_DIRECTORY_PATH="$(readlink -f "${SCRIPT_DIRECTORY}/../../")"
echo "Repository root directory path: ${REPOSITORY_ROOT_DIRECTORY_PATH}"

# Don't use ERR_LIBRARY_NOT_AVAILABLE because we didn't source common.sh yet
# shellcheck disable=SC1091 # do not follow
source "${SCRIPT_DIRECTORY}/common.sh" || exit 3

start_timestamp_aws_gcp_migration=$(date +%s)

# Destroy the demo platform services in reverse provisioning order to account
# for dependencies
echo "Destroing the demo platform"
# shellcheck disable=SC2154 # variable defined in common.sh
for ((i = ${#aws_to_gcp_migration_demo_terraservices[@]} - 1; i >= 0; i--)); do
  terraservice=${aws_to_gcp_migration_demo_terraservices[i]}
  destroy_terraservice "${terraservice}"

  rm -f backend.tf
  for configuration_file in "${core_platform_configuration_files[@]}"; do
    configuration_file_name="_${configuration_file}"
    rm -f "${configuration_file_name}"
  done
done

# Destroy the core platform services in reverse provisioning order to account
# for dependencies
echo "Destroying the core platform"
CORE_TERRASERVICES_DESTROY=""
# shellcheck disable=SC2154 # variable defined in common.sh
for ((i = ${#core_platform_terraservices[@]} - 1; i >= 0; i--)); do
  CORE_TERRASERVICES_DESTROY="${CORE_TERRASERVICES_DESTROY} ${core_platform_terraservices[i]}"
done
# Trim leading space
CORE_TERRASERVICES_DESTROY="${CORE_TERRASERVICES_DESTROY#"${CORE_TERRASERVICES_DESTROY%%[![:space:]]*}"}"
CORE_TERRASERVICES_DESTROY="${CORE_TERRASERVICES_DESTROY}" \
  "${ACP_PLATFORM_CORE_DIR}/teardown.sh"

end_timestamp_aws_gcp_migration=$(date +%s)
total_runtime_value_aws_gcp_migration=$((end_timestamp_aws_gcp_migration - start_timestamp_aws_gcp_migration))
echo "Total runtime (AWS to Google Cloud demo provisioning and configuration): $(date -d@${total_runtime_value_aws_gcp_migration} -u +%H:%M:%S)"
