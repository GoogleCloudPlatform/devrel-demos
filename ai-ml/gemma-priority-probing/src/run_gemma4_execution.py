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
Empirical Execution Engine for Gemma 4 E4B / Deep Architecture Probing.

Runs forward passes and J-Lens layer projections across all 34 layers,
computing real target token probabilities for conflict prompts (Authority vs. Recency),
and logs empirical trajectory data.
"""

import os
import sys
import json
import argparse
import math
import random
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SRC_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
ROOT_DIR = PROJECT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from j_lens_gemma import GemmaJLens

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

def prompt_id_seed(s):
    return str(s) if s else "seed_01"

def run_gemma4_probing(
    model_id: str = "google/gemma-4-e4b",
    target_prompt_id: str = "scenario_01_cloud_iam_stale_first",
    temperature: float = 0.7,
    prompt_text: str = "",
    target_choice_1: str = "",
    target_choice_2: str = "",
    dataset_path: str = "benchmark_seed_expanded.json",
    device: str = "cpu",
    output_path: str = str(DATA_DIR / "gemma_4_e4b_empirical_results.json"),
    restrict_to_fitted: bool = True,
    use_jacobians: bool = True,
    allow_logit_lens_fallback: bool = False,
    randomize_jacobians: bool = False
):
    print("==================================================")
    print(f"=== PROJECT LANTERN: GEMMA PROBING EXECUTION ===")
    print(f" Model ID: {model_id} | Target Prompt: {target_prompt_id}")
    print(f" Target Device: {device} | PyTorch Available: {HAS_TORCH}")
    print("==================================================")

    dataset_file = DATA_DIR / dataset_path
    if not dataset_file.exists():
        dataset_file = Path(dataset_path)
    if not dataset_file.exists():
        candidate_aiml = ROOT_DIR / "ai-ml" / "gemma-priority-probing" / "data" / dataset_path
        candidate_local = ROOT_DIR / "gemma-priority-probing" / "data" / dataset_path
        dataset_file = candidate_aiml if candidate_aiml.exists() else candidate_local
    with open(dataset_file, "r") as f:
        all_samples = json.load(f)

    # 2. Load Live Hugging Face PyTorch Model or fallback to Vertex AI
    hf_model = None
    hf_tokenizer = None
    device_str = device

    if not HAS_TORCH:
        raise RuntimeError("PyTorch is required for execution.")

    if torch.backends.mps.is_available():
        try:
            torch.mps.empty_cache()
        except Exception:
            pass

    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        hf_target = model_id

        print(f"[*] Loading Live PyTorch Model '{hf_target}' on {device_str.upper()}...")
        hf_tokenizer = AutoTokenizer.from_pretrained(hf_target)
        hf_model = AutoModelForCausalLM.from_pretrained(
            hf_target,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True
        )
        if device_str != "cpu":
            hf_model = hf_model.to(device_str)
        print(f"[✓] Live PyTorch Model '{hf_target}' successfully loaded on {device_str.upper()}!")
    except Exception as err:
        raise RuntimeError(f"Failed to load PyTorch Model '{hf_target}': {err}") from err

    try:
        with open(output_path, "r") as f:
            empirical_results = json.load(f)
    except FileNotFoundError:
        empirical_results = {
            "model_id": hf_target,
            "layers": hf_model.config.text_config.num_hidden_layers if hasattr(hf_model.config, "text_config") else hf_model.config.num_hidden_layers,
            "is_live_weights": True,
            "experiments": {}
        }
    
    j_lens_engine = GemmaJLens(hf_model, hf_tokenizer, device=device_str, model_id=hf_target)
    if use_jacobians:
        try:
            jac_file = DATA_DIR / f"jacobians_{hf_target.replace('/', '_')}.pt"
            if not jac_file.exists():
                cand_aiml = ROOT_DIR / "ai-ml" / "gemma-priority-probing" / "data" / f"jacobians_{hf_target.replace('/', '_')}.pt"
                cand_local = ROOT_DIR / "gemma-priority-probing" / "data" / f"jacobians_{hf_target.replace('/', '_')}.pt"
                jac_file = cand_aiml if cand_aiml.exists() else cand_local
            j_lens_engine.load_jacobians(str(jac_file), randomize_jacobians=randomize_jacobians)
            if hasattr(j_lens_engine, "jacobian_provenance"):
                empirical_results["jacobian_provenance"] = j_lens_engine.jacobian_provenance
        except Exception as e:
            raise RuntimeError(f"Could not load Jacobians for '{hf_target}': {e}") from e
    else:
        print("[*] Skipping Jacobian load (Logit-Lens Control Mode)")



    if target_prompt_id and target_prompt_id != "custom_prompt_input":
        # Apply target_choice overwrites to the matching sample, not dead code
        target_samples = [s for s in all_samples if s.get("id") == target_prompt_id]
        if not target_samples:
            raise ValueError(f"Prompt ID '{target_prompt_id}' not found in dataset!")
        for s in target_samples:
            if target_choice_1:
                s["target_stale"] = target_choice_1
            if target_choice_2:
                s["target_recent"] = target_choice_2
    else:
        target_samples = [{"id": "custom_prompt_input", "prompt": prompt_text}]

    for sample in target_samples:
        sample_id = sample.get("id", "sample_01")
        prompt = prompt_text if (prompt_text and sample_id == target_prompt_id) else sample["prompt"]
        stale_tok = sample.get("target_stale", sample.get("stale", "GCP"))
        recent_tok = sample.get("target_recent", sample.get("recent", "Cloud"))

        if target_choice_1:
            stale_tok = target_choice_1
        if target_choice_2:
            recent_tok = target_choice_2
            
        stale_tok = " " + stale_tok.lstrip(" ")
        recent_tok = " " + recent_tok.lstrip(" ")

        print(f"\n[Probing] Executing Live Model Forward Pass for '{sample_id}'...")

        generated_text = ""
        top_tokens = {}
        
        top_tokens = j_lens_engine.get_top_k_verbalizations(
            prompt, top_k=5, restrict_to_fitted=restrict_to_fitted, 
            allow_logit_lens_fallback=allow_logit_lens_fallback
        )

        try:
            inputs = hf_tokenizer(prompt, return_tensors="pt").to(device_str if device_str != "cpu" else "cpu")
            with torch.no_grad():
                outputs = hf_model.generate(**inputs, max_new_tokens=25, do_sample=False)
            generated_text = hf_tokenizer.decode(outputs[0], skip_special_tokens=True).replace(prompt, "").strip()
            print(f" -> Live Hugging Face Response: {generated_text!r}")
        except Exception as hf_err:
            raise RuntimeError(f"HF Generation error: {hf_err}") from hf_err

        probe_data = {
            recent_tok: {},
            stale_tok: {}
        }
        
        print(f" -> Running GemmaJLens over {j_lens_engine.num_layers} layers...")
        try:
            layer_probs = j_lens_engine.probe_tokens_across_layers(
                prompt, [recent_tok, stale_tok], 
                allow_logit_lens_fallback=allow_logit_lens_fallback, 
                restrict_to_fitted=restrict_to_fitted
            )
            probe_data = layer_probs
        except Exception as e:
            raise RuntimeError(f"J-Lens Probing failed: {e}") from e

        empirical_results["experiments"][sample_id] = {
            "prompt": prompt,
            "stale_target": stale_tok,
            "recent_target": recent_tok,
            "generated_text": generated_text,
            "top_tokens": top_tokens,
            "layer_trajectories": probe_data
        }

    # 3. Export results to JSON
    out_file = ROOT_DIR / output_path
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(empirical_results, f, indent=2)

    print(f"\n[✓] Empirical execution complete! Results saved to '{out_file.resolve()}'")
    return empirical_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Gemma Probing Execution")
    parser.add_argument("--model_id", type=str, default="google/gemma-4-e4b")
    parser.add_argument("--prompt_id", type=str, default="scenario_01_cloud_iam_stale_first")
    parser.add_argument("--prompt_text", type=str, default="")
    parser.add_argument("--target_choice_1", type=str, default="")
    parser.add_argument("--target_choice_2", type=str, default="")
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--restrict_to_fitted", action=argparse.BooleanOptionalAction, default=True, help="Speed up by skipping un-fitted early layers")
    parser.add_argument("--use_jacobians", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--allow_logit_lens_fallback", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--randomize_jacobians", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()
    run_gemma4_probing(
        model_id=args.model_id,
        target_prompt_id=args.prompt_id,
        prompt_text=args.prompt_text,
        target_choice_1=args.target_choice_1,
        target_choice_2=args.target_choice_2,
        device=args.device,
        restrict_to_fitted=args.restrict_to_fitted,
        use_jacobians=args.use_jacobians,
        allow_logit_lens_fallback=args.allow_logit_lens_fallback,
        randomize_jacobians=args.randomize_jacobians
    )
