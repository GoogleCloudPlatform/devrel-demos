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

"""Parse every YAML file (including multi-document files) with PyYAML.

Usage: python3 tools/check_yaml.py [ROOT]
"""
import os
import sys

import yaml

SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}


def main(argv):
    root = os.path.abspath(argv[1] if len(argv) > 1 else ".")
    bad = 0
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if not name.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(dirpath, name)
            count += 1
            try:
                with open(path, encoding="utf-8") as f:
                    list(yaml.safe_load_all(f))
            except yaml.YAMLError as e:
                bad += 1
                print(f"YAML error in {os.path.relpath(path, root)}: {e}")
    print(f"yaml: {count - bad}/{count} files parse")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
