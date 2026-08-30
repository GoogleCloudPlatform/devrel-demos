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

import json, sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from activation_patching import score, build_donor, load_model

def main():
    model_id = "google/gemma-4-e4b"
    device = "cpu"
    tok = AutoTokenizer.from_pretrained(model_id)
    print("Loading model on CPU...")
    model, device = load_model(model_id, device)
    
    from pathlib import Path
    data_candidate = Path(__file__).resolve().parent.parent / "data" / "conflict_dataset.json"
    ds_path = str(data_candidate) if data_candidate.exists() else "gemma-priority-probing/data/conflict_dataset.json"
    items = [d for d in json.load(open(ds_path)) if d["id"].endswith("_conflict")]
    
    for it in items:
        recipient = it["prompt"]
        stale_t = it["target_stale"]
        recent_t = it["target_recent"]
        
        # recipient base diff
        s_base, _, _ = score(model, tok, recipient, stale_t, device)
        r_base, _, _ = score(model, tok, recipient, recent_t, device)
        recipient_diff = r_base - s_base
        
        # donor base diff
        donor, marker, cand = build_donor(recipient, tok)
        s_donor, _, _ = score(model, tok, donor, stale_t, device)
        r_donor, _, _ = score(model, tok, donor, recent_t, device)
        donor_diff = r_donor - s_donor
        
        # context-free offset
        cf_prompt = ""
        s_cf, _, _ = score(model, tok, cf_prompt, stale_t, device)
        r_cf, _, _ = score(model, tok, cf_prompt, recent_t, device)
        cf_diff = r_cf - s_cf
        
        print(f"\nItem: {it['id']}")
        print(f"  Targets: {recent_t} (recent) vs {stale_t} (stale)")
        print(f"  Flip: '{marker}' -> '{cand}'")
        print(f"  Recipient Diff (logP(recent) - logP(stale)): {recipient_diff:.4f}")
        print(f"  Donor Diff:     {donor_diff:.4f}")
        print(f"  Ceiling Effect (Recipient - Donor): {recipient_diff - donor_diff:.4f}")
        print(f"  Context-Free Diff (Lexical offset): {cf_diff:.4f}")
        print(f"  Calibrated Recipient Diff: {recipient_diff - cf_diff:.4f}")
        print(f"  Calibrated Donor Diff:     {donor_diff - cf_diff:.4f}")

if __name__ == "__main__":
    main()
