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
Jacobian Lens (J-Lens) & Logit Lens Engine for Gemma Models.
Implements Jacobian Matrix J_l estimation and vocabulary logit projection.
Reference: Anthropic Transformer Circuits Workspace (July 6, 2026):
https://transformer-circuits.pub/2026/workspace
"""

import json
import torch
import torch.nn as nn
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Depth-fraction prior for the workspace band.
# Source: Gurnee et al. (2026), "Verbalizable Representations Form a Global
# Workspace in Language Models," Transformer Circuits Thread.
# Their workspace band is ~L38-L92 on a 0-100 reindexed depth scale (Sonnet 4.5).
# NOTE: Measured on frontier-scale models. Transfer to smaller/26-layer models
# is an open empirical question and should not be assumed as structural fact.
DEFAULT_WINDOW_PRIOR_FRAC = (0.38, 0.92)
DEFAULT_PEAK_PRIOR_FRAC = 0.65

def load_model_configs() -> dict:
    config_path = Path(__file__).parent / "model_configs.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Required model configuration file not found at {config_path.resolve()}.")
    with open(config_path) as f:
        raw_data = json.load(f)
        formatted = {}
        for key, val in raw_data.items():
            model_name = val.get("model_id", val.get("name", key))
            if "j_space_window" in val:
                raise ValueError(f"Legacy key 'j_space_window' found in model_configs.json for '{model_name}'. Use 'j_space_window_prior'.")
            if "j_space_peak" in val:
                raise ValueError(f"Legacy key 'j_space_peak' found. Use 'j_space_peak_prior'.")
            if "assembly_window" in val:
                raise ValueError(f"Legacy key 'assembly_window' found. Use 'assembly_window_prior'.")
                
            j_window = val.get("j_space_window_prior", [0,0])
            j_peak = val.get("j_space_peak_prior", 0)
            formatted[model_name] = {
                "num_layers": val["layers"],
                "j_space_window_prior": tuple(j_window),
                "j_space_window_measured": val.get("j_space_window_measured", None),
                "j_space_peak_prior": j_peak,
                "assembly_window_prior": tuple(val.get("assembly_window_prior", [0,0])),
                "d_model": val["d_model"]
            }
        return formatted

GEMMA_MODEL_CONFIGS = load_model_configs()

class GemmaJLens:
    """
    Hooking and Jacobian computation wrapper for Gemma models.
    """
    def __init__(self, model, tokenizer, device: str = "cpu", model_id: str = "google/gemma-4-e4b"):
        self.model = model
        self.model.eval()
        self.model.config.use_cache = False
        self.tokenizer = tokenizer
        self.device = device
        self.model_id = model_id
        self.num_layers = self._get_num_layers()
        self.config_meta = self._get_model_config()
        self.activations: Dict[int, torch.Tensor] = {}
        self.hooks = []
        self.jacobian_matrices: Dict[int, torch.Tensor] = {}

    def _get_d_model(self) -> int:
        if hasattr(self.model.config, "text_config"):
            config = self.model.config.text_config
        else:
            config = self.model.config
            
        for attr in ["hidden_size", "d_model", "dim", "embedding_dim"]:
            if hasattr(config, attr):
                return getattr(config, attr)
                
        if hasattr(self.model, "get_input_embeddings") and self.model.get_input_embeddings() is not None:
            return self.model.get_input_embeddings().weight.shape[1]
        elif hasattr(self.model, "embed_tokens") and hasattr(self.model.embed_tokens, "weight"):
            return self.model.embed_tokens.weight.shape[1]
        raise AttributeError(f"Could not dynamically determine d_model for model '{self.model_id}'.")

    def _get_model_config(self) -> dict:
        if self.model_id in GEMMA_MODEL_CONFIGS:
            return GEMMA_MODEL_CONFIGS[self.model_id]
        for k, v in GEMMA_MODEL_CONFIGS.items():
            if k in self.model_id:
                return v
        
        # Dynamic computation using explicit DEFAULT_WINDOW_PRIOR_FRAC heuristic prior
        num_layers = self.num_layers
        d_model = self._get_d_model()
        return {
            "num_layers": num_layers,
            "j_space_window_prior": (int(num_layers * DEFAULT_WINDOW_PRIOR_FRAC[0]), int(num_layers * DEFAULT_WINDOW_PRIOR_FRAC[1])),
            "j_space_window_measured": None,
            "j_space_peak_prior": int(num_layers * DEFAULT_PEAK_PRIOR_FRAC),
            "assembly_window_prior": (int(num_layers * 0.92), num_layers - 1),
            "d_model": d_model
        }

    def _get_num_layers(self) -> int:
        if hasattr(self.model.config, "text_config"):
            config = self.model.config.text_config
        else:
            config = self.model.config
            
        if hasattr(config, "num_hidden_layers"):
            return config.num_hidden_layers
        elif hasattr(config, "n_layer"):
            return config.n_layer
        elif hasattr(config, "num_layers"):
            return config.num_layers
        elif self.model_id in GEMMA_MODEL_CONFIGS:
            return GEMMA_MODEL_CONFIGS[self.model_id]["num_layers"]
        raise AttributeError(f"Could not determine layer count for model '{self.model_id}'.")

    def _get_layer_parent(self) -> nn.Module:
        if hasattr(self.model, "model") and hasattr(self.model.model, "language_model") and hasattr(self.model.model.language_model, "model") and hasattr(self.model.model.language_model.model, "layers"):
            return self.model.model.language_model.model
        elif hasattr(self.model, "model") and hasattr(self.model.model, "language_model") and hasattr(self.model.model.language_model, "layers"):
            return self.model.model.language_model
        elif hasattr(self.model, "model") and hasattr(self.model.model, "layers"):
            return self.model.model
        elif hasattr(self.model, "layers"):
            return self.model
        raise AttributeError("Could not identify layer module structure in model.")

    def _get_layer_module(self, layer_idx: int) -> nn.Module:
        return self._get_layer_parent().layers[layer_idx]

    def register_hooks(self):
        """Register forward hooks on all layer residual outputs."""
        self.remove_hooks()
        for layer_idx in range(self.num_layers):
            layer_module = self._get_layer_module(layer_idx)
            
            def hook_fn(module, input, output, idx=layer_idx):
                if isinstance(output, tuple):
                    self.activations[idx] = output[0]
                else:
                    self.activations[idx] = output
                    
            hook = layer_module.register_forward_hook(hook_fn)
            self.hooks.append(hook)

    def remove_hooks(self):
        for hook in self.hooks:
            hook.remove()
        self.hooks = []
        self.activations = {}

    @torch.no_grad()
    def compute_logit_lens(self, layer_idx: int, hidden_state: torch.Tensor) -> torch.Tensor:
        """
        Compute Logit Lens logits: softmax(W_U * norm(h_l))
        """
        # 1. Find the final norm layer from the exact same parent that owns the layers
        parent = self._get_layer_parent()
        if not hasattr(parent, "norm"):
            raise AttributeError("Could not find the final normalization layer (norm) in the parent module.")
        norm_layer = parent.norm
            
        normed = norm_layer(hidden_state)

        # 2. Unembed
        if hasattr(self.model, "lm_head"):
            logits = self.model.lm_head(normed)
        elif hasattr(self.model, "embed_tokens"):
            logits = torch.matmul(normed, self.model.embed_tokens.weight.T)
        else:
            raise AttributeError("Could not find unembedding layer (lm_head/embed_tokens).")
            
        # 3. Apply final logit softcapping (Gemma-2/4)
        config = self.model.config.text_config if hasattr(self.model.config, "text_config") else self.model.config
        softcap = getattr(config, "final_logit_softcapping", None) or 0.0
        if softcap > 0.0:
            logits = logits / softcap
            logits = torch.tanh(logits)
            logits = logits * softcap
            
        return logits

    def load_jacobians(self, pt_path: str, randomize_jacobians: bool = False):
        """Loads fitted Jacobian matrices from disk."""
        path = Path(pt_path)
        if not path.exists():
            raise FileNotFoundError(f"Jacobian matrices file not found at {path}")
        data = torch.load(path, map_location=self.device, weights_only=True)
        self.jacobian_matrices = data.get("matrices", data)
        if randomize_jacobians:
            for l in self.jacobian_matrices:
                if self.jacobian_matrices[l] is not None:
                    idx = torch.randperm(self.jacobian_matrices[l].size(0))
                    self.jacobian_matrices[l] = self.jacobian_matrices[l][idx]
        
        prov = data.get("_provenance", {})
        if prov and prov.get("model_id") != self.model_id:
            raise ValueError(f"Jacobian was fitted on {prov.get('model_id')}, loading into {self.model_id}")
            
        if prov and prov.get("dtype") != str(self.model.dtype).split(".")[-1] and str(self.model.dtype) != prov.get("dtype"):
            raise ValueError(f"Jacobian provenance dtype {prov.get('dtype')} does not match model dtype {self.model.dtype}")
            
        d = self.config_meta["d_model"]
        for l, J in self.jacobian_matrices.items():
            if J is not None and tuple(J.shape) != (d, d):
                raise ValueError(f"J_{l} has shape {tuple(J.shape)}, expected ({d},{d})")
                
        # Linearly interpolate missing layers between min and max fitted layer
        fit_layers = sorted([l for l, J in self.jacobian_matrices.items() if J is not None])
        interpolated = []
        if len(fit_layers) >= 2:
            min_l = min(fit_layers)
            max_l = max(fit_layers)
            for l in range(min_l, max_l):
                if l not in self.jacobian_matrices or self.jacobian_matrices[l] is None:
                    # find left and right anchor
                    left = max([x for x in fit_layers if x < l])
                    right = min([x for x in fit_layers if x > l])
                    alpha = (l - left) / (right - left)
                    J_left = self.jacobian_matrices[left]
                    J_right = self.jacobian_matrices[right]
                    self.jacobian_matrices[l] = (1 - alpha) * J_left + alpha * J_right
                    interpolated.append(l)
                    
        prov["interpolated_layers"] = interpolated
        self.jacobian_provenance = prov
        
        total_layers = len([J for J in self.jacobian_matrices.values() if J is not None])
        print(f"Loaded {len(fit_layers)} exact Jacobian matrices and interpolated {len(interpolated)} from {path}")

    @torch.no_grad()
    def compute_j_lens(self, layer_idx: int, hidden_state: torch.Tensor, allow_logit_lens_fallback: bool = False) -> torch.Tensor:
        """
        Compute J-Lens logits: softmax(W_U * norm(J_l * h_l))
        """
        if layer_idx in self.jacobian_matrices and self.jacobian_matrices[layer_idx] is not None:
            J_l = self.jacobian_matrices[layer_idx].to(hidden_state.device, dtype=hidden_state.dtype)
            transformed = torch.matmul(hidden_state, J_l.T)
        else:
            if not allow_logit_lens_fallback:
                raise RuntimeError(
                    f"No Jacobian J_{layer_idx} fitted. The J-lens requires a corpus-averaged "
                    f"Jacobian (Gurnee et al. 2026, Methods). Call fit_jacobians() first, load them, "
                    f"or use allow_logit_lens_fallback=True explicitly if the logit lens is what you want."
                )
            import warnings
            warnings.warn(f"J-Lens falling back to Logit Lens for layer {layer_idx}.")
            transformed = hidden_state
        return self.compute_logit_lens(layer_idx, transformed)

    def probe_tokens_across_layers(
        self, prompt: str, target_tokens: List[str], allow_logit_lens_fallback: bool = False,
        restrict_to_fitted: bool = True
    ) -> Dict[str, Dict[int, float]]:
        """
        Probe sequence probability of target strings across all intermediate layers.
        """
        results = {t: {} for t in target_tokens}
        
        layers_to_probe = range(self.num_layers)
        if restrict_to_fitted:
            if self.jacobian_matrices:
                layers_to_probe = sorted([l for l in self.jacobian_matrices.keys() if self.jacobian_matrices[l] is not None])
            else:
                layers_to_probe = [12, 22, 30, 36, 41]

        # Find common prefix length
        target_ids_list = [self.tokenizer.encode(t, add_special_tokens=False) for t in target_tokens]
        min_len = min(len(ids) for ids in target_ids_list) if target_ids_list else 0
        common_prefix_len = 0
        if min_len > 0:
            for i in range(min_len):
                if all(ids[i] == target_ids_list[0][i] for ids in target_ids_list):
                    common_prefix_len += 1
                else:
                    break

        for target_idx, target in enumerate(target_tokens):
            prompt_ids = self.tokenizer.encode(prompt, add_special_tokens=True)
            prompt_len = len(prompt_ids)
            
            target_ids = target_ids_list[target_idx]
            
            input_ids = prompt_ids + target_ids[:-1]
            input_tensor = torch.tensor([input_ids], device=self.device)
            
            self.register_hooks()
            with torch.no_grad():
                self.model(input_ids=input_tensor)
                
            # If target is identical to the common prefix (e.g. prefix match), score the last token
            start_idx = common_prefix_len if common_prefix_len < len(target_ids) else len(target_ids) - 1
            start_idx = max(0, start_idx)
            
            for layer_idx in layers_to_probe:
                if layer_idx in self.activations:
                    h_l = self.activations[layer_idx]
                    
                    seq_prob = 1.0
                    for i in range(start_idx, len(target_ids)):
                        t_id = target_ids[i]
                        pos = prompt_len - 1 + i
                        h_pos = h_l[:, pos, :]
                        
                        logits = self.compute_j_lens(layer_idx, h_pos, allow_logit_lens_fallback=allow_logit_lens_fallback)
                        probs = torch.softmax(logits, dim=-1)[0]
                        seq_prob *= probs[t_id].item()
                        
                    num_evaluated = len(target_ids) - start_idx
                    if num_evaluated > 0:
                        seq_prob = seq_prob ** (1.0 / num_evaluated)
                        
                    results[target][layer_idx] = seq_prob
                    
            self.remove_hooks()
            
        return results

    def get_top_k_verbalizations(
        self, prompt: str, top_k: int = 5, allow_logit_lens_fallback: bool = False, restrict_to_fitted: bool = True
    ) -> Dict[int, List[Tuple[str, float]]]:
        """
        Extract the top-k verbalizable tokens (J-Space content) at each layer.
        """
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        self.register_hooks()
        
        with torch.no_grad():
            self.model(**inputs)
            
        top_k_per_layer = {}
        layers_to_probe = range(self.num_layers)
        if restrict_to_fitted:
            if self.jacobian_matrices:
                layers_to_probe = sorted([l for l in self.jacobian_matrices.keys() if self.jacobian_matrices[l] is not None])
            else:
                layers_to_probe = [12, 22, 30, 36, 41]
            
        for layer_idx in layers_to_probe:
            if layer_idx in self.activations:
                h_l = self.activations[layer_idx][:, -1, :]
                logits = self.compute_j_lens(layer_idx, h_l, allow_logit_lens_fallback=allow_logit_lens_fallback)
                probs = torch.softmax(logits, dim=-1)[0]
                top_values, top_indices = torch.topk(probs, k=top_k)
                
                top_k_per_layer[layer_idx] = [
                    (self.tokenizer.decode([idx.item()]).strip(), val.item())
                    for val, idx in zip(top_values, top_indices)
                ]
                
        self.remove_hooks()
        return top_k_per_layer
