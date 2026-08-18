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
import math
from pathlib import Path
from run_gemma4_execution import run_gemma4_probing

no_context_prompt = "Question: What template should I use for project planning?\nAnswer:"
counterbalance_prompt = """Context:
[OFFICIAL GUIDELINE (2019)]
The mandatory core template for project planning is Cloud PDD.

[Team Update (Yesterday)]
We have migrated all templates. The new template is GCP PDD.

Question: What template should I use for project planning?
Answer:"""

print("\n--- Running No-Context Baseline (O2.1) ---")
res_no_context = run_gemma4_probing(
    target_prompt_id="custom_prompt_input",
    prompt_text=no_context_prompt,
    target_choice_1="GCP",
    target_choice_2="Cloud",
    device="cpu",
    use_jacobians=False,
    allow_logit_lens_fallback=True
)

print("\n--- Running Role Counterbalance (O2.2) ---")
res_counterbalance = run_gemma4_probing(
    target_prompt_id="custom_prompt_input",
    prompt_text=counterbalance_prompt,
    target_choice_1="Cloud", # stale
    target_choice_2="GCP",   # recent
    device="cpu",
    use_jacobians=False,
    allow_logit_lens_fallback=True
)

def get_l41_probs(res, sample_id, tok1, tok2):
    traj = res["experiments"][sample_id].get("top_tokens", res["experiments"][sample_id].get("layer_trajectories", {}))
    
    def get_prob(token_str):
        # The key might be integer 41 in memory, or string "41" after JSON serialization
        l41_data = traj.get(41, traj.get("41", []))
        if isinstance(l41_data, dict):
            return l41_data.get(token_str, 0.0)
        else:
            # list of [token, prob]
            for t, p in l41_data:
                if t == token_str:
                    return p
            return 0.0

    l41_1 = get_prob(tok1)
    l41_2 = get_prob(tok2)
    return l41_1, l41_2

try:
    nc_gcp, nc_cloud = get_l41_probs(res_no_context, "custom_prompt_input", "GCP", "Cloud")
    print(f"\nNo-Context L41 Probs -> Cloud: {nc_cloud:.4f}, GCP: {nc_gcp:.4f}")
    
    cb_cloud, cb_gcp = get_l41_probs(res_counterbalance, "custom_prompt_input", "Cloud", "GCP")
    print(f"Counterbalance L41 Probs -> Recent(GCP): {cb_gcp:.4f}, Stale(Cloud): {cb_cloud:.4f}")
    
    # Calculate delta safely
    if nc_gcp > 0 and nc_cloud > 0:
        print(f"\nNo-Context Delta (Cloud - GCP): {math.log(nc_cloud) - math.log(nc_gcp):.3f} nats")
    else:
        print(f"\nNo-Context Delta: Cannot compute log(0)")
        
    if cb_gcp > 0 and cb_cloud > 0:
        print(f"Counterbalance Content Effect (Cloud - GCP): {math.log(cb_cloud) - math.log(cb_gcp):.3f} nats")
        print(f"Counterbalance Position Effect (Recent - Stale): {math.log(cb_gcp) - math.log(cb_cloud):.3f} nats")
    else:
        print(f"Counterbalance Effects: Cannot compute log(0)")
except Exception as e:
    print(f"Could not extract probabilities: {e}")
