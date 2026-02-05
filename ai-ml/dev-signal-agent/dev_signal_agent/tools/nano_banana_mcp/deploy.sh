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

source ".env"

echo "Deploying MCP Server to Cloud Run..."
MCP_SERVICE_NAME="media-mcp"

gcloud run deploy "${MCP_SERVICE_NAME}" \
  --source . \
  --project "${GOOGLE_CLOUD_PROJECT}" \
  --region "${GOOGLE_CLOUD_RUN_LOCATION}" \
  --allow-unauthenticated \
  --clear-base-image \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI}" \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION}" \
  --set-env-vars GOOGLE_CLOUD_RUN_LOCATION="${GOOGLE_CLOUD_RUN_LOCATION}" \
  --set-env-vars AI_ASSETS_BUCKET="${AI_ASSETS_BUCKET}"
