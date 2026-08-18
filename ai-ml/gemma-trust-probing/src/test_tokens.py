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

import sys
import json
from transformers import AutoTokenizer

def test_tokens():
    tokenizer = AutoTokenizer.from_pretrained("google/gemma-4-e4b")
    
    with open("/path/to/your/project.json", "r") as f:
        dataset = json.load(f)
        
    unique_pairs = set()
    for item in dataset:
        stale = " " + item["target_stale"].lstrip(" ")
        recent = " " + item["target_recent"].lstrip(" ")
        unique_pairs.add((stale, recent))
        
    for stale, recent in unique_pairs:
        targets = [stale, recent]
        target_ids_list = [tokenizer.encode(t, add_special_tokens=False) for t in targets]

        min_len = min(len(ids) for ids in target_ids_list) if target_ids_list else 0
        common_prefix_len = 0
        if min_len > 0:
            for i in range(min_len):
                if all(ids[i] == target_ids_list[0][i] for ids in target_ids_list):
                    common_prefix_len += 1
                else:
                    break
                    
        assert stale != recent, f"Degenerate targets: {stale} == {recent}"
        assert common_prefix_len < min_len, f"Strict prefix: {stale} and {recent}"
        
        num_evaluated = []
        for i, t in enumerate(targets):
            start_idx = common_prefix_len if common_prefix_len < len(target_ids_list[i]) else len(target_ids_list[i]) - 1
            start_idx = max(0, start_idx)
            num_evaluated.append(len(target_ids_list[i]) - start_idx)
            
        print(f"Targets: {targets} | Common Prefix: {common_prefix_len} | Evaluated lengths: {num_evaluated}")

if __name__ == "__main__":
    test_tokens()
