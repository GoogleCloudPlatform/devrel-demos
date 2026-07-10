#!/bin/bash
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

# This script sets up the environment variables needed for manual
# deployment commands, specifically those using 'envsubst'.
#
# USAGE: source ./setup-env.sh
# Do NOT run this as a subshell (e.g. ./setup-env.sh) because the
# exported variables will be lost when the subshell exits.

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Ensure the script is being sourced, not executed directly.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo -e "${RED}❌ ERROR: This script must be sourced to modify your current shell environment.${NC}"
  echo -e "Please run it like this:"
  echo -e "${BOLD}  source ./setup-env.sh${NC}"
  echo -e "or"
  echo -e "${BOLD}  . ./setup-env.sh${NC}"
  exit 1
fi

echo -e "${BLUE}ℹ${NC} Loading environment variables..."

# 1. Load variables from .env if it exists
if [ -f ".env" ]; then
  echo -e "${BLUE}ℹ${NC} Found .env file. Exporting variables..."
  # Use allexport (-a) to export all defined variables, then source the file, then turn off allexport
  set -a
  source .env
  set +a
else
  echo -e "${RED}❌ ERROR: .env file not found in the current directory.${NC}"
  echo -e "Please ensure you have run a deployment script (like deploy.sh) to generate it, or create it from .env.example."
  return 1
fi

# 1.5 Verify all required variables are present
REQUIRED_VARS=(
  "GOOGLE_CLOUD_PROJECT"
  "GOOGLE_CLOUD_REGION"
  "ARTIFACT_REGISTRY_LOCATION"
  "ARTIFACT_REPO_NAME"
  "BQ_DATASET"
  "RESULTS_SUB"
  "RESULTS_TOPIC"
  "TASKS_SUBSCRIPTION"
  "TASKS_TOPIC"
)

MISSING_VARS=false
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo -e "${RED}❌ ERROR: Required variable '$var' is not set or is empty.${NC}"
    MISSING_VARS=true
  fi
done

if [ "$MISSING_VARS" = "true" ]; then
  echo -e "${YELLOW}⚠️  Please update your .env file with the missing variables and try again.${NC}"
  return 1
fi

# 2. Determine and export COMMIT_SHA
echo -e "${BLUE}ℹ${NC} Determining COMMIT_SHA for Docker image tags..."

if command -v git &> /dev/null && git rev-parse --short HEAD &> /dev/null; then
  if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  Git repository has uncommitted changes (dirty state).${NC}"
    export COMMIT_SHA="dirty-$(date +%s)"
  else
    export COMMIT_SHA=$(git rev-parse --short HEAD)
  fi
else
  echo -e "${YELLOW}⚠️  Git not detected or repository not initialized.${NC}"
  export COMMIT_SHA="manual-$(date +%s)"
fi

echo -e "${GREEN}✅ Setup complete!${NC}"
echo -e "\n${BOLD}Active Configuration:${NC}"
echo -e "  Project:    ${GOOGLE_CLOUD_PROJECT:-unset}"
echo -e "  Region:     ${GOOGLE_CLOUD_REGION:-unset}"
echo -e "  Repository: ${ARTIFACT_REGISTRY_LOCATION:-unset}-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT:-unset}/${ARTIFACT_REPO_NAME:-unset}"
echo -e "  Image Tag:  ${COMMIT_SHA}\n"
echo -e "You can now run commands like:"
echo -e "  ${BOLD}envsubst < k8s/agent.yaml | kubectl apply -f -${NC}"
