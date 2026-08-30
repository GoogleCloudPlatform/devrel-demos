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

import torch
import math
from transformers import AutoTokenizer, AutoModelForCausalLM

model_id = "google/gemma-4-e4b"
print(f"Loading {model_id} on CPU...")
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)
model.eval()

def get_probs(prompt, tok1_str, tok2_str):
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits[0, -1, :]
        probs = torch.softmax(logits, dim=-1)
        
    ids1 = tokenizer.encode(tok1_str, add_special_tokens=False)
    ids2 = tokenizer.encode(tok2_str, add_special_tokens=False)
    assert len(ids1) == 1, f"Token {tok1_str} is not a single token: {ids1}"
    assert len(ids2) == 1, f"Token {tok2_str} is not a single token: {ids2}"
    
    id1, id2 = ids1[-1], ids2[-1]
    
    return probs[id1].item(), probs[id2].item()

print("\n--- O2.1: No-Context Baseline (Full Vocabulary) ---")
nc_prompt = "Question: What template should I use for project planning?\nAnswer:"
p_gcp_nc, p_cloud_nc = get_probs(nc_prompt, " GCP", " Cloud")
print(f"No-Context Probs -> GCP: {p_gcp_nc:.8f}, Cloud: {p_cloud_nc:.8f}")

print("\n--- O2.2: Matched 2x2 Counterbalance ---")

template_stale_first = """Context:
[OFFICIAL GUIDELINE (2019)]
Official guidelines state that for Project Planning Template, the required configuration is {stale} PDD.

[Team Update (Yesterday)]
Update: The new updated specification for Project Planning Template is now {recent} PDD.

Question: What template should I use for project planning?
Answer:"""

template_recent_first = """Context:
[Team Update (Yesterday)]
Update: The new updated specification for Project Planning Template is now {recent} PDD.

[OFFICIAL GUIDELINE (2019)]
Official guidelines state that for Project Planning Template, the required configuration is {stale} PDD.

Question: What template should I use for project planning?
Answer:"""

# Quadrant 1: Stale=GCP, Recent=Cloud, Order=Stale-First
prompt_1 = template_stale_first.format(stale="GCP", recent="Cloud")
p_gcp_1, p_cloud_1 = get_probs(prompt_1, " GCP", " Cloud")

# Quadrant 2: Stale=GCP, Recent=Cloud, Order=Recent-First
prompt_2 = template_recent_first.format(stale="GCP", recent="Cloud")
p_gcp_2, p_cloud_2 = get_probs(prompt_2, " GCP", " Cloud")

# Quadrant 3: Stale=Cloud, Recent=GCP, Order=Stale-First
prompt_3 = template_stale_first.format(stale="Cloud", recent="GCP")
p_gcp_3, p_cloud_3 = get_probs(prompt_3, " GCP", " Cloud")

# Quadrant 4: Stale=Cloud, Recent=GCP, Order=Recent-First
prompt_4 = template_recent_first.format(stale="Cloud", recent="GCP")
p_gcp_4, p_cloud_4 = get_probs(prompt_4, " GCP", " Cloud")

print(f"Q1 (Stale=GCP, Recent=Cloud, Stale-First) -> GCP(Stale): {p_gcp_1:.4f}, Cloud(Recent): {p_cloud_1:.4f}")
print(f"Q2 (Stale=GCP, Recent=Cloud, Recent-First)-> GCP(Stale): {p_gcp_2:.4f}, Cloud(Recent): {p_cloud_2:.4f}")
print(f"Q3 (Stale=Cloud, Recent=GCP, Stale-First) -> Cloud(Stale): {p_cloud_3:.4f}, GCP(Recent): {p_gcp_3:.4f}")
print(f"Q4 (Stale=Cloud, Recent=GCP, Recent-First)-> Cloud(Stale): {p_cloud_4:.4f}, GCP(Recent): {p_gcp_4:.4f}")

import math

# e_i = log(P(Cloud)) - log(P(GCP))
effect_1 = math.log(p_cloud_1) - math.log(p_gcp_1)
effect_2 = math.log(p_cloud_2) - math.log(p_gcp_2)
effect_3 = math.log(p_cloud_3) - math.log(p_gcp_3)
effect_4 = math.log(p_cloud_4) - math.log(p_gcp_4)

token_effect = (effect_1 + effect_2 + effect_3 + effect_4) / 4
role_effect = (effect_1 + effect_2 - effect_3 - effect_4) / 4
order_effect = (effect_1 - effect_2 + effect_3 - effect_4) / 4
serial_pos_effect = (effect_1 - effect_2 - effect_3 + effect_4) / 4

print(f"\nEffects Decomposition (across 2x2 grid):")
print(f"Token Effect (Cloud vs GCP): {token_effect:.3f} nats")
print(f"Role/Semantic Effect (Recent vs Stale): {role_effect:.3f} nats")
print(f"Block-Order Main Effect: {order_effect:.3f} nats")
print(f"Serial Position Effect (Last-Mentioned): {serial_pos_effect:.3f} nats")
