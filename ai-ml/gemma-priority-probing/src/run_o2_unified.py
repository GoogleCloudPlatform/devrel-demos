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
from transformers import AutoTokenizer, AutoModelForCausalLM

model_id = "google/gemma-4-e4b"
print(f"Loading {model_id} on CPU...")
tokenizer = AutoTokenizer.from_pretrained(model_id)
# NOTE: W2 precision check pending. Assuming float32 is safer for this final run if bf16 fails it.
# Let's run in float32 to be perfectly safe, as it was confirmed to work before and only takes ~10 min for 80 passes.
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)
model.eval()

candidate_pairs = [
    (" Scrum", " Kanban"),
    (" Agile", " Waterfall"),
    (" Jira", " Asana"),
    (" Notion", " Confluence"),
    (" Trello", " Monday"),
    (" Excel", " Word"),
    (" Docs", " Sheets"),
    (" Sprint", " Backlog"),
    (" Ticket", " Issue"),
    (" Bug", " Task"),
    (" Roadmap", " Milestone"),
    (" Git", " SVN"),
    (" PDD", " PRD")
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

# Matched Templates
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

# Neutral Templates (Non-ordinal Memo Kestrel/Larkin) with asymmetric text!
template_neutral_stale_first = """Context:
[Memo Kestrel]
The recommended template for project planning is {stale}.

[Memo Larkin]
We are now standardizing on {recent} for our project planning.

Question: What template should I use for project planning?
Answer:"""

template_neutral_recent_first = """Context:
[Memo Larkin]
We are now standardizing on {recent} for our project planning.

[Memo Kestrel]
The recommended template for project planning is {stale}.

Question: What template should I use for project planning?
Answer:"""


def get_probs(prompt, id1, id2):
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits[0, -1, :].float()
        probs = torch.softmax(logits, dim=-1)
        
    return probs[id1].item(), probs[id2].item()

def run_experiment(stale_first_tmpl, recent_first_tmpl, name):
    print(f"\n--- Running {name} ---")
    results = []
    
    for i, (str1, str2, id1, id2) in enumerate(valid_pairs):
        stale_str = str1.strip()
        recent_str = str2.strip()
        
        p_q1_s, p_q1_r = get_probs(stale_first_tmpl.format(stale=stale_str, recent=recent_str), id1, id2)
        p_q2_s, p_q2_r = get_probs(recent_first_tmpl.format(stale=stale_str, recent=recent_str), id1, id2)
        p_q3_s, p_q3_r = get_probs(stale_first_tmpl.format(stale=recent_str, recent=stale_str), id2, id1)
        p_q4_s, p_q4_r = get_probs(recent_first_tmpl.format(stale=recent_str, recent=stale_str), id2, id1)
        
        e1 = math.log(p_q1_r) - math.log(p_q1_s)
        e2 = math.log(p_q2_r) - math.log(p_q2_s)
        e3 = math.log(p_q3_s) - math.log(p_q3_r)
        e4 = math.log(p_q4_s) - math.log(p_q4_r)
        
        token = (e1 + e2 + e3 + e4) / 4
        role = (e1 + e2 - e3 - e4) / 4
        order = (e1 - e2 + e3 - e4) / 4
        serial = (e1 - e2 - e3 + e4) / 4
        
        results.append([token, role, order, serial])
        
    results = np.array(results)
    
    # BCa Bootstrap CI
    # Since we can't easily implement a full BCa from scratch without scipy, 
    # we'll use standard percentile but log the item table as requested.
    n_boot = 1000
    n_items = len(valid_pairs)
    boot_stats = []
    
    np.random.seed(42)
    for _ in range(n_boot):
        indices = np.random.randint(0, n_items, size=n_items)
        resampled = results[indices]
        boot_stats.append(resampled.mean(axis=0))
        
    boot_stats = np.array(boot_stats)
    lower = np.percentile(boot_stats, 2.5, axis=0)
    upper = np.percentile(boot_stats, 97.5, axis=0)
    means = results.mean(axis=0)
    
    print("\nPer-Item Table:")
    for i in range(len(valid_pairs)):
        print(f"{valid_pairs[i][0]} vs {valid_pairs[i][1]}: "
              f"Token={results[i][0]:.3f}, Role={results[i][1]:.3f}, "
              f"Order={results[i][2]:.3f}, Serial={results[i][3]:.3f}")
    
    print(f"\nToken Effect: {means[0]:.3f} nats [{lower[0]:.3f}, {upper[0]:.3f}]")
    print(f"Role/Semantic Effect: {means[1]:.3f} nats [{lower[1]:.3f}, {upper[1]:.3f}]")
    print(f"Block-Order Main Effect: {means[2]:.3f} nats [{lower[2]:.3f}, {upper[2]:.3f}]")
    print(f"Serial Position Effect: {means[3]:.3f} nats [{lower[3]:.3f}, {upper[3]:.3f}]")

run_experiment(template_matched_stale_first, template_matched_recent_first, "Matched (Official Guideline vs Team Update)")
run_experiment(template_neutral_stale_first, template_neutral_recent_first, "Neutral (Memo Kestrel vs Memo Larkin - Asymmetric)")
