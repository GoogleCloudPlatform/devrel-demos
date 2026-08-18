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
Visualization Module for J-Space Trajectories & Probing Results.
Plots layer-by-layer target token probabilities for Authority vs. Recency conflict prompts.
Saves plots into the docs/plots directory.
"""

import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Import the single source of truth for configs
from j_lens_gemma import GEMMA_MODEL_CONFIGS

def plot_layer_trajectories(prob_data: dict, title: str, save_path: str = "docs/plots/j_space_trajectory.png", synthetic: bool = False):
    """
    Plots target token probabilities across layers.
    If synthetic=True, applies a translucent watermark 'SYNTHETIC — NOT DATA'.
    """
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    
    for token, layer_dict in prob_data.items():
        layers = sorted(layer_dict.keys())
        probs = [layer_dict[l] for l in layers]
        ax.plot(layers, probs, marker='o', linewidth=2, label=f"Token: '{token}'")
        
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_xlabel("Model Layer Index", fontsize=11)
    ax.set_ylabel("Logit Lens / J-Lens Token Probability", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(fontsize=11)

    if synthetic:
        fig.text(
            0.5, 0.5, "SYNTHETIC — NOT DATA",
            fontsize=36, color="red", alpha=0.18,
            ha="center", va="center", rotation=30, fontweight="bold"
        )

    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close(fig)
    print(f"Saved J-Space trajectory plot to {path.resolve()}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Visualize J-Space Trajectories")
    model_choices = list(GEMMA_MODEL_CONFIGS.keys())
    parser.add_argument("--model_id", type=str, default=model_choices[0], choices=model_choices)
    parser.add_argument("--synthetic", action="store_true", default=True, help="Watermark figure as synthetic data")
    args = parser.parse_args()

    config = GEMMA_MODEL_CONFIGS.get(args.model_id, list(GEMMA_MODEL_CONFIGS.values())[0])
    num_layers = config["num_layers"]
    peak_l = config.get("j_space_peak_prior", num_layers - 2)

    mock_data = {
        "GCP (Stale/Official)": {l: 0.05 + 0.8 * (l / num_layers)**2 if l < peak_l else 0.85 - 0.7 * ((l - peak_l) / (num_layers - peak_l))**2 for l in range(num_layers)},
        "Cloud (Recent/Brief)": {l: 0.02 + 0.1 * (l / num_layers) if l < peak_l else 0.12 + 0.75 * ((l - peak_l) / (num_layers - peak_l))**2 for l in range(num_layers)}
    }
    
    out_dir = "artifacts/synthetic" if args.synthetic else "artifacts/runs"
    plot_layer_trajectories(
        mock_data,
        title=f"{args.model_id} J-Space Probing ({num_layers} Layers): Authority (GCP) vs. Recency (Cloud)",
        save_path=f"{out_dir}/j_space_trajectory_{args.model_id.replace('/', '_')}.png",
        synthetic=args.synthetic
    )

if __name__ == "__main__":
    main()
