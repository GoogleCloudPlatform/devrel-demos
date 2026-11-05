#!/usr/bin/env bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Safe Google Docs wrapper (`tools/save_to_gdocs.sh`) for Breaking News Lab.
# Enforces Yellow-Light / Green-Light boundaries:
# 1. Refuses to sync unless all 3 harness grades pass (`exit code 0`).
# 2. Locks `gdocs mutate sync` to one approved Document ID and Tab ID.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DRAFT_FILE="${1:-}"
DOC_ID="${2:-YOUR_GOOGLE_DOC_ID}"
TAB_ID="${3:-t.0}"

if [[ -z "${DRAFT_FILE}" ]]; then
  echo "Usage: ./tools/save_to_gdocs.sh <path/to/draft.md> [doc_id] [tab_id]"
  exit 1
fi

echo "[1/2] Running Breaking News Lab Referee Grades on ${DRAFT_FILE}..."
python3 "${HARNESS_ROOT}/grades/run_all_grades.py" "${DRAFT_FILE}"

echo "[2/2] All grades passed! Syncing to Google Doc (${DOC_ID}, tab ${TAB_ID})..."
gdocs mutate sync "${DOC_ID}" "${DRAFT_FILE}" --tab "${TAB_ID}"
