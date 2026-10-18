#!/usr/bin/env python3
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

"""
Lark Memory - Local File Indexer
Scans a directory on your computer, generates 768-d EmbeddingGemma 2 vectors
via your cloud endpoint, and injects them into the Lark Memory app database.
"""

import os
import sys
import json
import time

from vertex_utils import get_token
from server import scan_and_index_folders

def scan_and_index(directory):
    if not os.path.isdir(directory):
        print(f"Directory not found: {directory}")
        return

    token = get_token()
    if not token:
        print("Please authenticate with `gcloud auth login` first.")
        return

    added, total = scan_and_index_folders([{"path": directory, "resolvedPath": directory}], token, silent=False)
    print(f"\nIndexed folder {directory}: {added} new items added ({total} total items in database).")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/index_folder.py <path-to-folder-on-your-computer>")
        print("Example: python3 scripts/index_folder.py ~/Documents")
        sys.exit(1)
    
    target_dir = os.path.expanduser(sys.argv[1])
    scan_and_index(target_dir)
