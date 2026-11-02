#!/usr/bin/env bash
# Copyright 2026 Google LLC
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

# Starts, locally, the two MCP servers the steps connect to:
#   agenda         http://localhost:8090/mcp
#   technologies   http://localhost:8092/mcp
# Leave it running in its own terminal. Not needed when AGENDA_MCP_URL and
# TECH_MCP_URL point at hosted servers.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p bin
go build -o bin/agendamcp ./agendamcp
go build -o bin/techmcp ./techmcp
bin/agendamcp &
agenda=$!
bin/techmcp &
technologies=$!
trap 'kill "$agenda" "$technologies" 2>/dev/null' EXIT
wait
