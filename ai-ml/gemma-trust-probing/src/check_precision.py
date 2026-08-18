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
from transformers import AutoTokenizer, AutoModelForCausalLM

model_id = "google/gemma-4-e4b"
print(f"Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_id)

def get_probs(model, prompt, id1, id2):
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits[0, -1, :].float() # cast back to float32 for softmax
        probs = torch.softmax(logits, dim=-1)
    return probs[id1].item(), probs[id2].item()

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

str1 = " GCP"
str2 = " Cloud"
id1 = tokenizer.encode(str1, add_special_tokens=False)[-1]
id2 = tokenizer.encode(str2, add_special_tokens=False)[-1]

def evaluate(model, name):
    print(f"\n--- Evaluating in {name} ---")
    stale_str = str1.strip()
    recent_str = str2.strip()
    
    p_q1_s, p_q1_r = get_probs(model, template_matched_stale_first.format(stale=stale_str, recent=recent_str), id1, id2)
    p_q2_s, p_q2_r = get_probs(model, template_matched_recent_first.format(stale=stale_str, recent=recent_str), id1, id2)
    p_q3_s, p_q3_r = get_probs(model, template_matched_stale_first.format(stale=recent_str, recent=stale_str), id2, id1)
    p_q4_s, p_q4_r = get_probs(model, template_matched_recent_first.format(stale=recent_str, recent=stale_str), id2, id1)
    
    e1 = math.log(p_q1_r) - math.log(p_q1_s)
    e2 = math.log(p_q2_r) - math.log(p_q2_s)
    e3 = math.log(p_q3_s) - math.log(p_q3_r)
    e4 = math.log(p_q4_s) - math.log(p_q4_r)
    
    print(f"e1: {e1:.4f}")
    print(f"e2: {e2:.4f}")
    print(f"e3: {e3:.4f}")
    print(f"e4: {e4:.4f}")
    
    serial = (e1 - e2 - e3 + e4) / 4
    print(f"Serial Position Effect: {serial:.4f}")

print("Loading bf16 model...")
model_bf16 = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16)
model_bf16.eval()
evaluate(model_bf16, "bfloat16")
del model_bf16

print("Loading fp32 model...")
model_fp32 = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)
model_fp32.eval()
evaluate(model_fp32, "float32")
