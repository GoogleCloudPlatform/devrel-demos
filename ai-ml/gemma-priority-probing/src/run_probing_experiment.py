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
Main Experiment Runner for Gemma J-Space Probing & IAFR Telemetry.
Evaluates expanded benchmark seed, tracks J-Space activations, computes IAFR,
and exports telemetry logs for Project Lantern.
"""

import os
import json
import argparse
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from j_lens_gemma import GemmaJLens, GEMMA_MODEL_CONFIGS
from lantern_tracer import LanternTracer
from visualize_j_space import plot_layer_trajectories

def main():
    parser = argparse.ArgumentParser(description="Run J-Space Probing and IAFR telemetry on Gemma models.")
    model_choices = list(GEMMA_MODEL_CONFIGS.keys())
    parser.add_argument("--model_id", type=str, default=model_choices[0], choices=model_choices, help="Hugging Face model ID")
    parser.add_argument("--dataset_path", type=str, default="benchmark_seed_expanded.json", help="Path to benchmark seed dataset JSON")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"))
    parser.add_argument("--max_samples", type=int, default=20, help="Number of benchmark samples to evaluate in run")
    args = parser.parse_args()

    print(f"=== Project Lantern: Gemma J-Space & IAFR Telemetry Run ===")
    print(f"Model ID: {args.model_id} | Device: {args.device}")
    print(f"Dataset: {args.dataset_path} (Evaluating up to {args.max_samples} samples)")

    if not Path(args.dataset_path).exists():
        raise FileNotFoundError(f"Dataset file {args.dataset_path} not found. Run expand_benchmark_seed.py first.")

    with open(args.dataset_path) as f:
        dataset = json.load(f)[:args.max_samples]

    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    
    # AutoConfig Dynamic Architecture Validation
    try:
        from transformers import AutoConfig
        cfg = AutoConfig.from_pretrained(args.model_id)
        n_layers = getattr(cfg, "num_hidden_layers", getattr(cfg, "n_layer", None))
        d_model = getattr(cfg, "hidden_size", getattr(cfg, "d_model", None))
        declared = GEMMA_MODEL_CONFIGS.get(args.model_id)
        if declared and n_layers is not None and d_model is not None:
            assert n_layers == declared["num_layers"], (
                f"CONFIG DRIFT: {args.model_id} HF config reports {n_layers} layers, declared {declared['num_layers']}"
            )
            assert d_model == declared["d_model"], (
                f"CONFIG DRIFT: {args.model_id} HF config reports d_model={d_model}, declared {declared['d_model']}"
            )
            print(f"✓ Verified AutoConfig architecture: {n_layers} layers, d_model={d_model}")
    except Exception as e:
        print(f"Warning: AutoConfig validation skipped: {e}")

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype=torch.float16 if args.device != "cpu" else torch.float32,
        device_map="auto" if args.device != "cpu" else None
    )

    j_lens = GemmaJLens(model, tokenizer, device=args.device, model_id=args.model_id)
    tracer = LanternTracer(experiment_name=f"lantern_iafr_{args.model_id.replace('/', '_')}", model_id=args.model_id)

    all_results = {}
    for idx, sample in enumerate(dataset):
        sample_id = sample["id"]
        category = sample.get("category", "general")
        prompt = sample["prompt"]
        stale_target = sample["target_stale"]
        recent_target = sample["target_recent"]
        
        print(f"\n[{idx+1}/{len(dataset)}] Evaluating: {sample_id} ({category})...")
        
        inputs = tokenizer(prompt, return_tensors="pt").to(args.device)
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=15, do_sample=False)
        generated_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
        print(f"  Model Output: '{generated_text}'")

        probe_res = j_lens.probe_tokens_across_layers(prompt, [stale_target, recent_target])
        top_k_res = j_lens.get_top_k_verbalizations(prompt, top_k=3)

        tracer.log_agent_run(
            prompt_id=sample_id,
            category=category,
            prompt_text=prompt,
            stale_target=stale_target,
            recent_target=recent_target,
            selected_output=generated_text,
            j_space_top_tokens=top_k_res
        )

        all_results[sample_id] = {
            "output": generated_text,
            "target_probes": probe_res,
            "top_verbalizations": {str(k): v for k, v in top_k_res.items()}
        }

    import datetime
    all_results["_provenance"] = {
        "synthetic": False,
        "model_id": args.model_id,
        "device": args.device,
        "samples_evaluated": len(dataset),
        "utc_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
    }

    # WARNING: The outputs generated by this script correspond to items #8 and #9 in the DATA_MANIFEST.
    # They are explicitly DEPRECATED and quarantined due to constraint violations.
    # DO NOT CITE AS AGGREGATE. Official publishable results are in data/results/o2_results_ad_series_FINAL.json.
    with open(f"jspace_results_{args.model_id.replace('/', '_')}_DO_NOT_CITE_AS_AGGREGATE.json", "w") as out_f:
        json.dump(all_results, out_f, indent=2)

    tracer.export_traces("lantern_telemetry_traces_DO_NOT_CITE_AS_AGGREGATE.json")
    metrics = tracer.compute_iafr_metrics()
    
    print("\n==================================================")
    print("=== PROJECT LANTERN: IAFR BASELINE METRICS ===")
    print(f" Total Runs Evaluated: {metrics['total_runs']}")
    print(f" Information Attributable Failure Rate (IAFR): {metrics['iafr_rate_percent']:.1f}% ({metrics['iafr_failures']}/{metrics['total_runs']} runs defaulted to stale/corrupted info)")
    print(f" Success Rate (Recent Info Adoption): {metrics['success_rate_percent']:.1f}%")
    print(f" Ambiguous Rate: {metrics['ambiguous_rate_percent']:.1f}%")
    print(" Category IAFR Breakdown:")
    for cat, rate in metrics.get("category_iafr_breakdown", {}).items():
        print(f"   - {cat}: {rate:.1f}% IAFR")
    print("==================================================")

if __name__ == "__main__":
    main()
