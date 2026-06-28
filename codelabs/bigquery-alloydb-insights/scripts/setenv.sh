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

# --- Set Logging Config ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_info()  { echo -e "${CYAN}ℹ️  ${BOLD}$1${NC}"; }
print_ok()    { echo -e "${GREEN}✅ $1${NC}"; }
print_warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Determine the script's directory (works even when sourced)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DIR/../.env"

if [ -f "$ENV_FILE" ]; then
    print_info "Loading environment variables from $ENV_FILE..."
    # Export all non-commented variables from the .env file cleanly
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*# || -z "$line" ]] && continue
        export "$line"
    done < "$ENV_FILE"
    # Validate that the critical variables were actually found in the .env file
    if [ -z "${PROJECT_ID:-}" ] || [ -z "${REGION:-}" ]; then
        print_warn ".env was loaded, but is missing PROJECT_ID or REGION."
        print_info "   Please re-run scripts/setup_lab.sh to configure your environment."
        return 1 2>/dev/null || exit 1
    fi
    print_ok "Environment loaded successfully: PROJECT_ID=$PROJECT_ID, REGION=$REGION"
else
    print_error ".env file not found at $ENV_FILE"
    print_info "   Please execute scripts/setup_lab.sh first to configure your environment."
    return 1 2>/dev/null || exit 1
fi
