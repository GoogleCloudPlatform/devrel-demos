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

import os
import sys
import torch
import math
import numpy as np
from scipy import stats
from transformers import AutoTokenizer, AutoModelForCausalLM

model_id = "google/gemma-4-e4b"
print(f"Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_id)

candidate_pairs = [
    (" Scrum", " Kanban"),
    (" Agile", " Waterfall"),
    (" Ticket", " Issue"),
    (" Roadmap", " Milestone"),
    (" Task", " Bug"),
    (" Epic", " Story"),
    (" Sprint", " Backlog"),
    (" Board", " List"),
    (" Card", " Chart"),
    (" Plan", " Draft"),
    (" Goal", " Phase"),
    (" Flow", " Cycle"),
    (" Spec", " Brief"),
    (" Stage", " Step"),
    (" Grid", " Table"),
    (" Scope", " Scale"),
    (" Note", " Memo")
]

valid_pairs = []
for p1, p2 in candidate_pairs:
    id1 = tokenizer.encode(p1, add_special_tokens=False)
    id2 = tokenizer.encode(p2, add_special_tokens=False)
    if len(id1) == 1 and len(id2) == 1:
        valid_pairs.append((p1, p2, id1[-1], id2[-1]))
        if len(valid_pairs) == 10:
            break

print(f"Found {len(valid_pairs)} valid single-token congruent entity pairs.")

template_matched_stale_first = """Context:
[OFFICIAL GUIDELINE (2019)]
Official guidelines state that for Project Planning Template, the required configuration is {stale}.

[Team Update (Yesterday)]
Update: The new updated specification for Project Planning Template is now {recent}.

Question: What template should I use for project planning?
Answer:"""

template_matched_recent_first = """Context:
[Team Update (Yesterday)]
Update: The new updated specification for Project Planning Template is now {recent}.

[OFFICIAL GUIDELINE (2019)]
Official guidelines state that for Project Planning Template, the required configuration is {stale}.

Question: What template should I use for project planning?
Answer:"""

# Reverted to V-version verbatim blocks to guarantee neutral control
template_neutral_stale_first_v_version = """Context:
[Memo Kestrel]
The recommended template for project planning is {stale}.

[Memo Larkin]
The recommended template for project planning is {recent}.

Question: What template should I use for project planning?
Answer:"""

template_neutral_recent_first_v_version = """Context:
[Memo Larkin]
The recommended template for project planning is {recent}.

[Memo Kestrel]
The recommended template for project planning is {stale}.

Question: What template should I use for project planning?
Answer:"""

def get_probs(model, prompt, id1, id2):
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits[0, -1, :].float()
        probs = torch.softmax(logits, dim=-1)
    return probs[id1].item(), probs[id2].item()

def evaluate_pairs(model, template_stale_first, template_recent_first):
    results = []
    
    for str1, str2, id1, id2 in valid_pairs:
        stale_str = str1.strip()
        recent_str = str2.strip()
        
        p_q1_s, p_q1_r = get_probs(model, template_stale_first.format(stale=stale_str, recent=recent_str), id1, id2)
        p_q2_s, p_q2_r = get_probs(model, template_recent_first.format(stale=stale_str, recent=recent_str), id1, id2)
        p_q3_s, p_q3_r = get_probs(model, template_stale_first.format(stale=recent_str, recent=stale_str), id2, id1)
        p_q4_s, p_q4_r = get_probs(model, template_recent_first.format(stale=recent_str, recent=stale_str), id2, id1)
        
        e1 = math.log(p_q1_r) - math.log(p_q1_s)
        e2 = math.log(p_q2_r) - math.log(p_q2_s)
        e3 = math.log(p_q3_s) - math.log(p_q3_r)
        e4 = math.log(p_q4_s) - math.log(p_q4_r)
        
        token = (e1 + e2 + e3 + e4) / 4
        role = (e1 + e2 - e3 - e4) / 4
        order = (e1 - e2 + e3 - e4) / 4
        serial = (e1 - e2 - e3 + e4) / 4
        
        results.append([token, role, order, serial])
        
    return np.array(results)

def print_stats(results, name):
    print(f"\n--- {name} ---")
    
    print("\nPer-Item Table:")
    for i in range(len(valid_pairs)):
        print(f"{valid_pairs[i][0].strip()} vs {valid_pairs[i][1].strip()}: "
              f"Token={results[i][0]:.3f}, Role={results[i][1]:.3f}, "
              f"Order={results[i][2]:.3f}, Serial={results[i][3]:.3f}")
              
    effects = ["Token", "Role/Semantic", "Block-Order", "Serial Position"]
    means = np.mean(results, axis=0)
    
    for i in range(4):
        # Edge case: if all values are identical (e.g. exactly 0.0), scipy bootstrap might error out
        if np.var(results[:, i]) == 0:
            print(f"{effects[i]} Effect: {means[i]:.3f} nats [{means[i]:.3f}, {means[i]:.3f}]")
        else:
            res = stats.bootstrap((results[:, i],), np.mean, method='bca', confidence_level=0.95, random_state=42)
            print(f"{effects[i]} Effect: {means[i]:.3f} nats [{res.confidence_interval.low:.3f}, {res.confidence_interval.high:.3f}]")

def run_y_series():
    if len(valid_pairs) < 10:
        print(f"ERROR: Only found {len(valid_pairs)} valid pairs. Need at least 10.")
        return

    print("\nLoading fp32 model...")
    model_fp32 = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)
    model_fp32.eval()
    
    print("\n=== CONDITION A: Neutral (V-Version verbatim blocks, fp32, 10 Pairs) ===")
    results_neutral = evaluate_pairs(model_fp32, template_neutral_stale_first_v_version, template_neutral_recent_first_v_version)
    print_stats(results_neutral, "Neutral Template")
    
    print("\n=== CONDITION B: Matched (Guideline vs Update, fp32, 10 Pairs) ===")
    results_matched = evaluate_pairs(model_fp32, template_matched_stale_first, template_matched_recent_first)
    print_stats(results_matched, "Matched Template")
    
    print("\n=== PAIRED DIFFERENCE (Neutral Serial - Matched Serial) ===")
    paired_diff = results_neutral[:, 3] - results_matched[:, 3]
    mean_diff = np.mean(paired_diff)
    if np.var(paired_diff) == 0:
        print(f"Suppression Effect (Neutral - Matched Serial): {mean_diff:.3f} nats [{mean_diff:.3f}, {mean_diff:.3f}]")
    else:
        res_diff = stats.bootstrap((paired_diff,), np.mean, method='bca', confidence_level=0.95, random_state=42)
        print(f"Suppression Effect (Neutral - Matched Serial): {mean_diff:.3f} nats [{res_diff.confidence_interval.low:.3f}, {res_diff.confidence_interval.high:.3f}]")

if __name__ == "__main__":
    run_y_series()
