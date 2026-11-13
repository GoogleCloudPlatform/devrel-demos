#!/usr/bin/env bash
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

# Static checks, offline self-tests and the leak check for containers/k8s-revisited.
# Usage: tools/verify.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0
step() { printf '\n== %s\n' "$1"; }
bad() { printf '   FAIL: %s\n' "$1"; fail=1; }

step "bash -n on every script"
n=0
while IFS= read -r -d '' f; do
  n=$((n + 1))
  bash -n "$f" || bad "$f"
done < <(find . -name '*.sh' -not -path '*/.git/*' -print0)
echo "   checked $n scripts"

step "YAML parse"
python3 tools/check_yaml.py . || bad "YAML parse"

step "license headers"
python3 tools/check_headers.py . || bad "license headers"

step "go vet and go build (root module)"
if command -v go >/dev/null 2>&1; then
  if go vet ./... && go build ./...; then echo "   ok"; else bad "go vet/build"; fi
else
  bad "go not found"
fi

step "python compileall (skips the intentional Python 2 task fixtures under tasks/)"
py_dirs=()
for d in shared tools ep0*/bench ep0*/viz; do [ -d "$d" ] && py_dirs+=("$d"); done
if python3 -m compileall -q -x "/tasks/" "${py_dirs[@]}" >/dev/null; then echo "   ok"; else bad "compileall"; fi

step "agent-check self-test (offline, fake model)"
if PYTHONPATH=shared/agent-check python3 -m unittest discover -s shared/agent-check/tests -q; then echo "   ok"; else bad "agent-check self-test"; fi
if [ -x shared/agent-check/.venv/bin/python ]; then
  step "agent-check ADK adapter test (offline, with google-adk from shared/agent-check/.venv)"
  if PYTHONPATH=shared/agent-check shared/agent-check/.venv/bin/python -m unittest discover -s shared/agent-check/tests -q; then echo "   ok"; else bad "agent-check ADK adapter test"; fi
fi

if [ -d shared/workloads/coding-agent-loop ]; then
  step "coding-agent-loop replay test (offline)"
  if PYTHONPATH=shared/workloads/coding-agent-loop python3 -m unittest discover -s shared/workloads/coding-agent-loop/tests -q; then echo "   ok"; else bad "coding-agent-loop replay test"; fi
fi

step "Python CLIs answer --help"
n=0
cli_dirs=()
for d in ep0*/bench ep0*/viz shared/workloads; do [ -d "$d" ] && cli_dirs+=("$d"); done
if [ ${#cli_dirs[@]} -gt 0 ]; then
  while IFS= read -r -d '' f; do
    n=$((n + 1))
    PYTHONPATH="shared/bench:shared/agent-check:shared/workloads/coding-agent-loop" python3 "$f" --help >/dev/null 2>&1 || bad "$f --help"
  done < <(find "${cli_dirs[@]}" -name '*.py' -not -name '__init__.py' -not -path '*/tests/*' -not -path '*/tasks/*' -not -path '*/coding_agent_loop/*' -print0 2>/dev/null)
fi
echo "   checked $n CLIs"

step "kind stays in the finale (episodes run on GKE)"
kind_hits="$(python3 - <<'PY'
import pathlib
import re

pat = re.compile(r"\bkind (create|delete|load)\b|kindest/node|KIND_CONFIG|\bkind-(up|down)\b")
hits = []
for p in sorted(pathlib.Path(".").rglob("*")):
    if not p.is_file() or ".git" in p.parts or p.parts[0] == "tools" or p.parts[0].startswith("ep08"):
        continue
    if p.name not in ("Makefile", "README.md") and p.suffix not in (".sh", ".mk"):
        continue
    for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
        if pat.search(line):
            hits.append(f"{p}:{i}: {line.strip()}")
print("\n".join(hits))
PY
)"
if [ -n "$kind_hits" ]; then printf '%s\n' "$kind_hits"; bad "kind referenced outside the finale"; else echo "   ok"; fi

step "leak check"
python3 tools/leak_check.py . || bad "leak check"

if command -v shellcheck >/dev/null 2>&1; then
  step "shellcheck (optional)"
  find . -name '*.sh' -not -path '*/.git/*' -print0 | xargs -0 shellcheck -S warning || bad "shellcheck"
fi

echo
if [ "$fail" -ne 0 ]; then
  echo "verify: FAILED"
  exit 1
fi
echo "verify: all checks passed"
