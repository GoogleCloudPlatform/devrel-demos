#!/bin/bash
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "${SCRIPT_DIR}/.."

source ".env"

if [[ "${AGENT_ENGINE_ID}" == "" ]]; then
    AGENT_ENGINE_ID=$(python3 "${SCRIPT_DIR}/get_agent_engine.py" --agent-name "${AGENT_NAME}" --project-id "${GOOGLE_CLOUD_PROJECT}" --location "${GOOGLE_CLOUD_LOCATION}" | tail -1)
    echo "AGENT_ENGINE_ID=\"${AGENT_ENGINE_ID}\"" >> ".env"
fi

adk deploy cloud_run \
    --project="${GOOGLE_CLOUD_PROJECT}" \
    --region="${GOOGLE_CLOUD_LOCATION}" \
    --service_name="${AGENT_NAME}" \
    --app_name="${AGENT_NAME}" \
    --session_service_uri="agentengine://${AGENT_ENGINE_ID}" \
    --memory_service_uri="agentengine://${AGENT_ENGINE_ID}" \
    --trace_to_cloud \
    --with_ui \
    ./agent \
    -- --allow-unauthenticated --set-env-vars=GOOGLE_GENAI_USE_VERTEXAI=TRUE
