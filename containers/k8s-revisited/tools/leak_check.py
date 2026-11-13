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

"""Fail if any file in the public tree matches an internal marker.

Usage: python3 tools/leak_check.py [ROOT]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}
SKIP_FILES = {os.path.join(HERE, "leak-markers.txt"), os.path.abspath(__file__)}


def load_markers(path):
    markers = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            markers.append(re.compile(line))
    return markers


def is_text(path):
    try:
        with open(path, "rb") as f:
            chunk = f.read(4096)
        return b"\0" not in chunk
    except OSError:
        return False


def scan(root, markers):
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = os.path.abspath(os.path.join(dirpath, name))
            if path in SKIP_FILES or not is_text(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, 1):
                    for m in markers:
                        if m.search(line):
                            hits.append((os.path.relpath(path, root), lineno, m.pattern, line.strip()[:120]))
    return hits


def main(argv):
    root = os.path.abspath(argv[1] if len(argv) > 1 else os.path.join(HERE, ".."))
    markers = load_markers(os.path.join(HERE, "leak-markers.txt"))
    hits = scan(root, markers)
    for rel, lineno, pattern, text in hits:
        print(f"{rel}:{lineno}: matches {pattern!r}: {text}")
    if hits:
        print(f"leak check: {len(hits)} match(es)")
        return 1
    print("leak check: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
