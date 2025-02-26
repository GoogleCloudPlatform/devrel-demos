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
source "${REPOSITORY_ROOT_DIRECTORY_PATH}/devrel-demos/containers/aws-gcp-migration/common.sh" || exit 3

if [ ! -e "${ACCELERATED_PLATFORMS_REPOSITORY_PATH}/.git" ]; then
  echo "Cloning the Accelerated Platforms repository to ${ACCELERATED_PLATFORMS_REPOSITORY_PATH}"
  git -C "${SCRIPT_DIRECTORY}" clone "https://github.com/GoogleCloudPlatform/accelerated-platforms.git"
else
  echo "Skip cloning the accelerated platforms repository because we already cloned it"
  git -C "${ACCELERATED_PLATFORMS_REPOSITORY_PATH}" fetch
fi

# TODO: refactor this command to switch to a commit on main after we merge
# https://github.com/GoogleCloudPlatform/accelerated-platforms/pull/70
git -C "${ACCELERATED_PLATFORMS_REPOSITORY_PATH}" checkout 6f38e62

start_timestamp_aws_gcp_migration=$(date +%s)

echo "Provisioning the core platform"
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable serviceusage.googleapis.com
# shellcheck disable=SC1091,SC2034,SC2154 # Variable is used in other scripts
CORE_TERRASERVICES_APPLY="${core_platform_terraservices[*]}" \
  "${ACP_PLATFORM_CORE_DIR}/deploy.sh"

# Load core platform configuration variables
# shellcheck disable=SC1091
source "${ACP_PLATFORM_BASE_DIR}/_shared_config/scripts/set_environment_variables.sh" "${ACP_PLATFORM_BASE_DIR}/_shared_config"

for service in "${aws_to_gcp_migration_demo_terraservices[@]}"; do
  cd "${AWS_TO_GCP_DEMO_TERRAFORM_DIRECTORY_PATH}/${service}"
  if [ ! -e "${TERRAFORM_GCS_BACKEND_FILE_NAME}" ]; then
    cat >"${TERRAFORM_GCS_BACKEND_FILE_NAME}" <<EOF
bucket = "${terraform_bucket_name}"
EOF
  fi

  for configuration_file in "${core_platform_configuration_files[@]}"; do
    configuration_file_name="_${configuration_file}"
    if [ ! -e "${configuration_file_name}" ]; then
      ln -sv "${ACP_PLATFORM_SHARED_CONFIG_DIR}/${configuration_file}" "${configuration_file_name}"
    fi
  done

  provision_terraservice "${service}"
done

end_timestamp_aws_gcp_migration=$(date +%s)
total_runtime_value_aws_gcp_migration=$((end_timestamp_aws_gcp_migration - start_timestamp_aws_gcp_migration))
echo "Total runtime (AWS to GCP demo provisioning and configuration): $(date -d@${total_runtime_value_aws_gcp_migration} -u +%H:%M:%S)"
