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

original_10_pairs = [
    (" Python", " Java"),
    (" Linux", " MacOS"),
    (" Windows", " Unix"),
    (" Azure", " AWS"),
    (" GCP", " Cloud"),
    (" Oracle", " MySQL"),
    (" React", " Angular"),
    (" Vue", " Svelte"),
    (" iOS", " Android"),
    (" Web", " Mobile")
]

new_7_pairs = [
    (" Scrum", " Kanban"),
    (" Agile", " Waterfall"),
    (" Jira", " Asana"),
    (" Notion", " Confluence"),
    (" Trello", " Monday"),
    (" Ticket", " Issue"),
    (" Roadmap", " Milestone")
]

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

template_neutral_stale_first_x_version = """Context:
[Memo Kestrel]
The recommended template for project planning is {stale}.

[Memo Larkin]
For project planning, the template we use is {recent}.

Question: What template should I use for project planning?
Answer:"""

template_neutral_recent_first_x_version = """Context:
[Memo Larkin]
For project planning, the template we use is {recent}.

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

def evaluate_pairs(model, pairs, template_stale_first, template_recent_first):
    results = []
    cell_values = []
    
    for str1, str2 in pairs:
        id1 = tokenizer.encode(str1, add_special_tokens=False)[-1]
        id2 = tokenizer.encode(str2, add_special_tokens=False)[-1]
        
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
        cell_values.append([e1, e2, e3, e4])
        
    return np.array(results), np.array(cell_values)


def print_stats(results, pairs, name):
    print(f"\n--- {name} ---")
    
    def boot_mean(data, axis):
        return np.mean(data, axis=axis)
        
    print("\nPer-Item Table:")
    for i in range(len(pairs)):
        print(f"{pairs[i][0].strip()} vs {pairs[i][1].strip()}: "
              f"Token={results[i][0]:.3f}, Role={results[i][1]:.3f}, "
              f"Order={results[i][2]:.3f}, Serial={results[i][3]:.3f}")
              
    effects = ["Token", "Role/Semantic", "Block-Order", "Serial Position"]
    means = np.mean(results, axis=0)
    
    for i in range(4):
        res = stats.bootstrap((results[:, i],), np.mean, method='bca', confidence_level=0.95, random_state=42)
        print(f"{effects[i]} Effect: {means[i]:.3f} nats [{res.confidence_interval.low:.3f}, {res.confidence_interval.high:.3f}]")

def isolation_x1_x2():
    print("\n=== ISOLATION X1(a): Precision (Matched, Original 10 Pairs) ===")
    
    print("Loading bf16 model...")
    model_bf16 = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16)
    model_bf16.eval()
    results_bf16, cells_bf16 = evaluate_pairs(model_bf16, original_10_pairs, template_matched_stale_first, template_matched_recent_first)
    print_stats(results_bf16, original_10_pairs, "Matched (bf16, original 10 pairs)")
    del model_bf16
    
    print("\nLoading fp32 model...")
    model_fp32 = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)
    model_fp32.eval()
    results_fp32, cells_fp32 = evaluate_pairs(model_fp32, original_10_pairs, template_matched_stale_first, template_matched_recent_first)
    print_stats(results_fp32, original_10_pairs, "Matched (fp32, original 10 pairs)")
    
    delta = np.abs(cells_fp32 - cells_bf16)
    mean_delta = np.mean(delta)
    print(f"\nMean |Δ| across all 10 items * 4 cells (fp32 vs bf16): {mean_delta:.4f} nats")
    
    print("\n=== ISOLATION X1(b): Stimulus (Neutral V-Version, fp32, New 7 Pairs) ===")
    results_v_neutral, _ = evaluate_pairs(model_fp32, new_7_pairs, template_neutral_stale_first_v_version, template_neutral_recent_first_v_version)
    print_stats(results_v_neutral, new_7_pairs, "Neutral (V-Version, fp32, New 7 Pairs)")
    
    print("\n=== X3/X4: Final Run (Neutral X-Version vs Matched, fp32, New 7 Pairs) ===")
    results_x_neutral, _ = evaluate_pairs(model_fp32, new_7_pairs, template_neutral_stale_first_x_version, template_neutral_recent_first_x_version)
    print_stats(results_x_neutral, new_7_pairs, "Neutral (X-Version, fp32, New 7 Pairs)")
    
    results_matched_7, _ = evaluate_pairs(model_fp32, new_7_pairs, template_matched_stale_first, template_matched_recent_first)
    print_stats(results_matched_7, new_7_pairs, "Matched (fp32, New 7 Pairs)")
    
    print("\n=== X4: Paired Difference (Neutral Serial - Matched Serial) ===")
    paired_diff = results_x_neutral[:, 3] - results_matched_7[:, 3]
    mean_diff = np.mean(paired_diff)
    res_diff = stats.bootstrap((paired_diff,), np.mean, method='bca', confidence_level=0.95, random_state=42)
    print(f"Suppression Effect (Neutral - Matched Serial): {mean_diff:.3f} nats [{res_diff.confidence_interval.low:.3f}, {res_diff.confidence_interval.high:.3f}]")

if __name__ == "__main__":
    isolation_x1_x2()
