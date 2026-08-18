#!/usr/bin/env python3

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

"""
Jacobian Lens Fitter for Project Lantern.

Computes the empirical Jacobian matrices J_l over a prompt corpus as specified
in Gurnee et al. (2026), "Verbalizable Representations Form a Global Workspace".
J_l = E_{t, t' >= t, prompt} [ d h_{target, t'} / d h_{l, t} ]

Usage:
  python3 fit_j_lens.py --model_id google/gemma-4-e4b --corpus_file data/corpus.txt
"""

import os
import argparse
import datetime
import hashlib
import warnings
import torch
from pathlib import Path
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
import subprocess

def get_git_revision_hash() -> str:
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
    except Exception:
        return "unknown"

def validate_jacobians(num_layers, jacobian_matrices, target_layer_idx, allow_bad_fit=False):
    """At layers near the target, J_l should approach a scalar multiple of I. If it doesn't, the fit is wrong."""
    print("\n[+] Validating Jacobian matrices convergence towards Identity (Scale-Invariant):")
    
    fitted_layers = sorted([l for l in jacobian_matrices.keys() if jacobian_matrices[l] is not None])
    
    if not fitted_layers:
        return
        
    sample_J = jacobian_matrices[fitted_layers[0]]
    d = sample_J.shape[0]
    I = torch.eye(d, device=sample_J.device, dtype=sample_J.dtype)
    
    prev_dist = float('inf')
    for l in fitted_layers:
        J = jacobian_matrices[l]
        
        alpha = torch.trace(J).item() / d
        norm_alpha_I = torch.norm(alpha * I, p='fro').item()
        
        if norm_alpha_I == 0:
            dist = float('inf')
        else:
            dist = torch.norm(J - alpha * I, p='fro').item() / norm_alpha_I
            
        print(f"    L{l}: ||J - αI||_F / ||αI||_F = {dist:.4f} (α={alpha:.4f})")
        
        # Warn if distance doesn't decrease monotonically (sparse anchors may fluctuate)
        if prev_dist != float('inf') and dist > prev_dist + 0.01:
            if not allow_bad_fit:
                raise ValueError(f"Jacobian convergence failed! L{l} distance ({dist:.4f}) is worse than previous layer ({prev_dist:.4f}).")
            else:
                print(f"    [WARNING] L{l} distance ({dist:.4f}) is worse than previous layer ({prev_dist:.4f}).")
        prev_dist = dist

        if l == target_layer_idx and dist > 0.01:
            raise ValueError(f"Target layer Jacobian did not converge to Identity! Distance = {dist:.4f}")

@torch.enable_grad()
def fit_jacobians(model, tokenizer, corpus, fit_layers=None, target_layer_idx=None, device="cpu"):
    num_layers = model.config.text_config.num_hidden_layers if hasattr(model.config, "text_config") else model.config.num_hidden_layers
    d_model = model.config.text_config.hidden_size if hasattr(model.config, "text_config") else model.config.hidden_size
    
    # Default to final layer
    if target_layer_idx is None:
         target_layer_idx = num_layers - 1 # 0-indexed, so num_layers-1 is final

    if fit_layers is None:
         fit_layers = [target_layer_idx]

    print(f"[*] Target Layer Index: {target_layer_idx} (Final Layer)")
    print(f"[*] d_model: {d_model}")
    print(f"[*] Number of layers to fit: {len(fit_layers)} (Layers: {fit_layers})")
    
    # Freeze all parameters to save memory; we only need gradients w.r.t hidden states
    for param in model.parameters():
        param.requires_grad = False
        
    J_global_avg = {l: torch.zeros(d_model, d_model, device=device, dtype=torch.float32) for l in fit_layers}
    
    # Pre-compute min layer to start graph
    min_fit_layer = min(fit_layers)
    
    for prompt_idx, prompt in enumerate(corpus):
        print(f"\n[+] Processing Prompt {prompt_idx+1}/{len(corpus)}: {prompt[:30]}...")
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        seq_len = inputs.input_ids.shape[1]
        
        captured_activations = {}
        handles = []
        
        # Helper hook function
        def make_hook(layer_idx):
            def hook(module, inp, out):
                t = out[0] if isinstance(out, tuple) else out
                
                # Start autograd graph here if it's the earliest layer we need
                if layer_idx == min_fit_layer:
                    t = t.detach().requires_grad_(True)
                    
                t.retain_grad()
                captured_activations[layer_idx] = t
                
                if isinstance(out, tuple):
                    return (t,) + out[1:]
                return t
            return hook
            
        # Register hooks for target layer and earlier
        if hasattr(model, "model") and hasattr(model.model, "language_model") and hasattr(model.model.language_model, "model") and hasattr(model.model.language_model.model, "layers"):
            layers_module = model.model.language_model.model.layers
        elif hasattr(model, "model") and hasattr(model.model, "language_model") and hasattr(model.model.language_model, "layers"):
            layers_module = model.model.language_model.layers
        elif hasattr(model, "model") and hasattr(model.model, "layers"):
            layers_module = model.model.layers
        elif hasattr(model, "layers"):
            layers_module = model.layers
        else:
            raise AttributeError("Could not identify layers module structure in model.")
        for l in fit_layers:
            handles.append(layers_module[l].register_forward_hook(make_hook(l)))
            
        outputs = model(**inputs, output_hidden_states=False)
        
        h_target = captured_activations[target_layer_idx]
        
        # Probe backward to verify gradients land correctly
        model.zero_grad()
        probe_grad = torch.zeros_like(h_target)
        probe_grad[0, 0, 0] = 1.0
        h_target.backward(gradient=probe_grad, retain_graph=True)
        assert captured_activations[min_fit_layer].grad is not None, "Gradient did not flow to earlier layers! Model may be frozen incorrectly or missing grad hooks."
        
        # Zero out the probe grads
        for l in fit_layers:
            if captured_activations[l].grad is not None:
                captured_activations[l].grad = None

        J_prompt = {l: torch.zeros(d_model, d_model, device=device, dtype=torch.float32) for l in fit_layers}
        
        # We average over source positions t. The sum over t' >= t is the target broadcast term.
        # This is a flat expectation over source positions E_t[ sum_{t' >= t} d(h_target_t')/d(h_l_t) ]
        normalization_factor = seq_len
        
        # Anthropic Jacobian estimator optimization:
        # Instead of looping over t_prime and injecting cotangents one-by-one (O(T * d_model) backwards),
        # we inject 1.0 at ALL target positions t' simultaneously for a given dimension.
        # Causal masking ensures that gradients flowing back to source token t only come from target tokens t' >= t.
        # Therefore, act.grad[0, t, :] is exactly sum_{t' >= t} d(h_target_t')/d(h_l_t).
        # We simply sum over t to get the total sum, and divide by seq_len.
        batch_size = 64
        for dim_start in tqdm(range(0, d_model, batch_size), desc=f"Dimensions (L={target_layer_idx})"):
            dim_end = min(dim_start + batch_size, d_model)
            current_bs = dim_end - dim_start
            
            model.zero_grad()
            grad_out = torch.zeros(current_bs, 1, seq_len, d_model, device=device, dtype=h_target.dtype)
            for i in range(current_bs):
                grad_out[i, 0, :, dim_start + i] = 1.0 
            
            inputs_tuple = tuple(captured_activations[l] for l in fit_layers)
            
            grads = torch.autograd.grad(
                outputs=h_target,
                inputs=inputs_tuple,
                grad_outputs=grad_out,
                retain_graph=True,
                is_grads_batched=True
            )
            
            for idx, l in enumerate(fit_layers):
                g = grads[idx]
                if g is not None:
                    # Sum over all source positions t
                    grad_sum = g[:, 0, :, :].to(torch.float32).sum(dim=1)
                    J_prompt[l][dim_start:dim_end, :] += grad_sum
                        
        for h in handles:
            h.remove()
            
        # Normalize per-prompt
        if normalization_factor > 0:
            for l in fit_layers:
                J_prompt[l] /= normalization_factor
                J_global_avg[l] += J_prompt[l]
                
    # Average across all prompts
    if len(corpus) > 0:
        for l in fit_layers:
            J_global_avg[l] /= len(corpus)
            
    # For layers after target, J_l is undefined because they are downstream of the target.
    # Exclude them by setting to None instead of Identity.
    for l in range(num_layers):
        if l not in fit_layers:
            J_global_avg[l] = None
        
    return J_global_avg

@torch.enable_grad()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_id", type=str, default="google/gemma-4-e4b")
    parser.add_argument("--corpus_file", type=str, required=True, help="Newline-delimited prompt corpus (>=100 prompts recommended; paper uses 1000)")
    parser.add_argument("--corpus_size", type=int, default=10)
    parser.add_argument("--fit_layers", type=str, default="12,22,30,36", help="Comma-separated list of layers to fit exact J")
    parser.add_argument("--allow_bad_fit", action="store_true", help="Allow J fit to fail monotonicity without crashing")
    parser.add_argument("--device", type=str, default="mps" if torch.backends.mps.is_available() else "cpu")
    parser.add_argument("--out_dir", type=str, default="gemma-trust-probing/data")
    args = parser.parse_args()

    print(f"=== Project Lantern: Jacobian Lens Fitter ===")
    print(f"Model ID: {args.model_id} | Device: {args.device}")
    
    if not os.path.exists(args.corpus_file):
        raise FileNotFoundError(f"Corpus file not found: {args.corpus_file}")

    with open(args.corpus_file, "r") as f:
        full_corpus = [l.strip() for l in f if l.strip()]
        
    corpus = full_corpus[:args.corpus_size]
    total_tokens = sum(len(c.split()) for c in corpus) # rough estimate

    fit_layers = sorted(list(set([int(x.strip()) for x in args.fit_layers.split(",") if x.strip()])))

    provenance = {
        "model_id": args.model_id,
        "corpus_sha256": hashlib.sha256(open(args.corpus_file, 'rb').read()).hexdigest(),
        "corpus_n_prompts": len(corpus),
        "corpus_n_unique": len(set(corpus)),
        "corpus_n_tokens": int(total_tokens),
        "target_layer_idx": -1, # will be populated dynamically
        "sketch_method": "none",
        "sketch_dim": -1,
        "num_fit_layers": len(fit_layers),
        "fit_layers": fit_layers,
        "interpolated_layers": [], # filled by load_jacobians
        "n_positions_sampled": "all",
        "target_position_mode": "future_inclusive",
        "dtype": "float32",
        "device": args.device,
        "code_git_sha": get_git_revision_hash(),
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    if len(corpus) < 10:
        warnings.warn(f"Corpus of {len(corpus)} prompts is below the paper's minimum useful size (~10). "
                      f"Fitted J will encode position artifacts, not verbalization structure.")

    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    
    config = AutoConfig.from_pretrained(args.model_id)
    n_layers = config.text_config.num_hidden_layers if hasattr(config, "text_config") else config.num_hidden_layers
    d_model = config.text_config.hidden_size if hasattr(config, "text_config") else config.hidden_size
    if n_layers != 42 or d_model != 2560:
        raise ValueError(f"Geometry assert failed: expected 42 layers and 2560 d_model, got {n_layers} / {d_model}")
        
    # ALWAYS load in FP32 on MPS when we compute gradients to avoid catastrophic precision loss
    dtype = torch.float32 if args.device == "mps" else (torch.float16 if args.device != "cpu" else torch.float32)
    model = AutoModelForCausalLM.from_pretrained(args.model_id, torch_dtype=dtype)
    model.eval()
    model.config.use_cache = False
    if args.device != "cpu":
        model = model.to(args.device)

    # ensure the target layer is included in the hook if not explicitly specified
    num_layers = model.config.text_config.num_hidden_layers if hasattr(model.config, "text_config") else model.config.num_hidden_layers
    target_layer_idx = num_layers - 1
    if target_layer_idx not in fit_layers:
         fit_layers.append(target_layer_idx)
         fit_layers.sort()
         provenance["fit_layers"] = fit_layers
         provenance["num_fit_layers"] = len(fit_layers)
         
    provenance["target_layer_idx"] = target_layer_idx
    provenance["sketch_dim"] = -1

    J_matrices = fit_jacobians(model, tokenizer, corpus, fit_layers=fit_layers, target_layer_idx=target_layer_idx, device=args.device)
    
    # Save Integrity Checks
    for l, J in J_matrices.items():
        if J is not None:
            if not torch.isfinite(J).all():
                raise ValueError(f"Jacobian matrix for layer {l} contains NaN or Inf.")
            if J.abs().sum() == 0:
                raise ValueError(f"Jacobian matrix for layer {l} is all zeros.")

    out_path = Path(args.out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    safe_name = args.model_id.replace("/", "_")
    file_path = out_path / f"jacobians_{safe_name}.pt"

    torch.save({
        "matrices": J_matrices,
        "_provenance": provenance
    }, file_path)

    print(f"\n[✓] Jacobian matrices fitted and saved to {file_path}")
    print(f"Provenance: {provenance}")

    validate_jacobians(num_layers, J_matrices, target_layer_idx, allow_bad_fit=args.allow_bad_fit)

if __name__ == "__main__":
    main()
