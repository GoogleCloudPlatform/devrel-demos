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

"""Check that every source file carries the Apache-2.0 license header.

Usage: python3 tools/check_headers.py [ROOT]
"""
import os
import re
import sys

EXTS = {".go", ".py", ".sh", ".yaml", ".yml", ".mk"}
NAMES = {"Makefile", "Dockerfile"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}
COPYRIGHT = re.compile(r"Copyright 20\d\d Google LLC")
LICENSE = "Licensed under the Apache License, Version 2.0"


def needs_header(name):
    return os.path.splitext(name)[1] in EXTS or name in NAMES


def main(argv):
    root = os.path.abspath(argv[1] if len(argv) > 1 else ".")
    missing = []
    checked = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if not needs_header(name):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8", errors="replace") as f:
                head = "".join(f.readline() for _ in range(20))
            checked += 1
            if not (COPYRIGHT.search(head) and LICENSE in head):
                missing.append(os.path.relpath(path, root))
    for rel in missing:
        print(f"missing license header: {rel}")
    print(f"license headers: {checked - len(missing)}/{checked} files ok")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
