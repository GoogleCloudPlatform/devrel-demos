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
import torch.nn.functional as F
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM

SRC_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SRC_DIR.parent
sys.path.insert(0, str(SRC_DIR))
from j_lens_gemma import GemmaJLens

def test_fidelity(model_id="google/gemma-4-e4b", device="cpu"):
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)
    model.eval()
    if device != "cpu":
        model = model.to(device)

    j_lens = GemmaJLens(model, tokenizer, device=device, model_id=model_id)
    jac_path = str(PROJECT_DIR / "data" / f"jacobians_{model_id.replace('/', '_')}.pt")
    j_lens.load_jacobians(jac_path)
    
    stale_prompt = "Context:\n[OFFICIAL GUIDELINE (2019)]\nThe mandatory core template for project planning is GCP PDD.\n\n[Team Update (Yesterday)]\nWe have migrated all templates. The new template is Cloud PDD.\n\nQuestion: What template should I use for project planning?\nAnswer:"
    
    inputs_stale = tokenizer(stale_prompt, return_tensors="pt").to(device)

    # 1. Get clean activations for stale
    j_lens.register_hooks()
    with torch.no_grad():
        model(**inputs_stale)
    stale_acts = {ly: act.clone() for ly, act in j_lens.activations.items()}
    j_lens.remove_hooks()

    pos = inputs_stale.input_ids.shape[1] - 1
    target_layer = 41
    
    print(f"--- S3: Relative Epsilon Sweep & Layer Offset Check ---")
    
    J_36 = j_lens.jacobian_matrices[36]
    
    torch.manual_seed(42)
    d_model = J_36.shape[0]
    num_directions = 10
    
    # Generate 10 random unit vectors
    directions = []
    for _ in range(num_directions):
        v = torch.randn(d_model, device=device)
        v = v / torch.norm(v)
        directions.append(v)
        
    relative_epsilons = [0.01, 0.1, 0.5, 1.0]
    layers_to_test = [35, 36, 37]
    
    for l in layers_to_test:
        print(f"\nEvaluating J_36 against perturbations at Layer {l}")
        h_norm = torch.norm(stale_acts[l][0, pos, :]).item()
        
        for rel_eps in relative_epsilons:
            cos_sims = []
            r2_opts = []
            c_opts = []
            
            # The absolute epsilon is a fraction of the layer norm
            abs_eps = rel_eps * h_norm
            
            for v in directions:
                delta_hl = abs_eps * v
                
                def get_injection_hook(injection_vector, target_pos):
                    def hook(module, input, output):
                        if isinstance(output, tuple):
                            output[0][0, target_pos, :] += injection_vector
                        else:
                            output[0, target_pos, :] += injection_vector
                        return output
                    return hook
                    
                target_module = j_lens._get_layer_parent().layers[l]
                handle = target_module.register_forward_hook(get_injection_hook(delta_hl, pos))
                
                j_lens.register_hooks()
                with torch.no_grad():
                    model(**inputs_stale)
                perturbed_acts = {ly: act.clone() for ly, act in j_lens.activations.items()}
                j_lens.remove_hooks()
                handle.remove()
                
                true_dh41 = perturbed_acts[target_layer][0, pos, :] - stale_acts[target_layer][0, pos, :]
                
                # Predict using J_36.T (even if injected at L35 or L37, to test offset)
                pred_dh41 = torch.matmul(delta_hl, J_36.T)
                
                # Metrics
                cos_sim = F.cosine_similarity(true_dh41.unsqueeze(0), pred_dh41.unsqueeze(0)).item()
                
                # Scale-Opt R^2
                dot_true_pred = torch.dot(true_dh41, pred_dh41).item()
                dot_pred_pred = torch.dot(pred_dh41, pred_dh41).item()
                c_opt = dot_true_pred / dot_pred_pred if dot_pred_pred > 1e-12 else 0.0
                
                pred_dh41_opt = c_opt * pred_dh41
                ss_res_opt = torch.sum((true_dh41 - pred_dh41_opt) ** 2).item()
                ss_tot = torch.sum(true_dh41 ** 2).item()
                if ss_tot == 0: ss_tot = 1e-12
                r2_opt = 1.0 - (ss_res_opt / ss_tot)
                
                cos_sims.append(cos_sim)
                r2_opts.append(r2_opt)
                c_opts.append(c_opt)
                
            cos_tensor = torch.tensor(cos_sims)
            r2_tensor = torch.tensor(r2_opts)
            c_tensor = torch.tensor(c_opts)
            
            avg_cos = cos_tensor.mean().item()
            std_cos = cos_tensor.std().item()
            avg_r2 = r2_tensor.mean().item()
            std_r2 = r2_tensor.std().item()
            avg_c = c_tensor.mean().item()
            std_c = c_tensor.std().item()
            
            print(f"Rel-Eps {rel_eps:4.2f} (Abs: {abs_eps:5.1f}) -> Avg Cosine: {avg_cos:7.4f} \u00b1 {std_cos:6.4f} | Avg Scale-Opt R^2: {avg_r2:7.4f} \u00b1 {std_r2:6.4f} | c_opt: {avg_c:5.2f} \u00b1 {std_c:4.2f}")

if __name__ == "__main__":
    test_fidelity()
