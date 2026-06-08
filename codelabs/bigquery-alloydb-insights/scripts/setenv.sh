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

# Determine the script's directory (works even when sourced)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DIR/../.env"

if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE..."
    # Export all non-commented variables from the .env file cleanly
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*# || -z "$line" ]] && continue
        export "$line"
    done < "$ENV_FILE"
    echo "✅ Environment loaded successfully: PROJECT_ID=$PROJECT_ID, REGION=$REGION"
else
    echo "❌ Error: .env file not found at $ENV_FILE"
    echo "   Please execute scripts/setup_lab.sh first to configure your environment."
    return 1 2>/dev/null || exit 1
fi
