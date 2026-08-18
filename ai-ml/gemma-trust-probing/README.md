# Gemma Trust Probing: Mechanistic Interpretability & Agent Trust Evaluation

> **Tracing Autonomous Agent Information Needs & Probing Mechanistic Trust Circuits on Google Gemma 4-e4b**

This repository is an open-source research toolkit for probing and visualizing layer-by-layer neural representations in Transformer models (specifically **Google Gemma 4-e4b**) when evaluating empirical conflict prompts (**Authority Bias vs. Recency Bias**).

---

## 📁 Repository Structure

```
gemma-trust-probing/
├── .gitattributes                    # Git LFS configuration for *.pt tensors
├── data/                             # Datasets, Stimuli & Results
│   ├── benchmark_seed_expanded.json
│   ├── conflict_dataset.json
│   ├── conflict_dataset_counterbalanced.json
│   ├── jacobians_google_gemma-4-e4b.pt
│   ├── corpus.txt
│   ├── corpus_deduped.txt
│   ├── corpus_in_distribution.txt
│   ├── results/                      # Canonical Publication Results
│   │   ├── o2_results_ad_series_FINAL.json
│   │   └── o2_results_ad_series_FINAL.txt
│   ├── no_cite_but_useful/           # Methodological Pilot Datasets
│   │   ├── gemma_4_e4b_empirical_results_FINAL_UNCOUNTERBALANCED_DO_NOT_CITE_AS_AGGREGATE.json
│   │   └── patching_results_authority_CELLS_FINAL_DO_NOT_CITE_AS_AGGREGATE.json
├── docs/                             # Documentation & Manifests
│   ├── DATA_MANIFEST.md
│   ├── METHOD.md
│   └── REPLICATION_LOG.md
├── src/                              # Probing Engine & Series Execution
│   ├── activation_patching.py
│   ├── check_precision.py
│   ├── counterbalance_dataset.py
│   ├── create_deduped_corpus.py
│   ├── dataset_curation.py
│   ├── diagnostic.py
│   ├── expand_benchmark_seed.py
│   ├── fit_j_lens.py
│   ├── j_lens_gemma.py
│   ├── lantern_tracer.py
│   ├── model_configs.json
│   ├── requirements.txt
│   ├── run_aa_series.py
│   ├── run_ab_series.py
│   ├── run_ac_series.py
│   ├── run_ad_series.py
│   ├── run_gemma4_execution.py
│   ├── run_o2_controls.py
│   ├── run_o2_matched.py
│   ├── run_o2_neutral.py
│   ├── run_o2_unified.py
│   ├── run_probing_experiment.py
│   ├── run_x_series.py
│   ├── run_y_series.py
│   ├── run_z_series.py
│   ├── setup_env.sh
│   ├── smoke_test_batched.py
│   ├── smoke_test_l36.py
│   ├── test_jacobian_fidelity.py
│   ├── test_tokens.py
│   └── visualize_j_space.py
├── LICENSE                           # Apache 2.0 License
└── README.md                         # Project documentation
```

---

## ⚡ Quick Start

### 1. Environment & Setup
```bash
# Set up Python environment
source src/setup_env.sh
pip install -r src/requirements.txt
```

### 2. Run AD-Series Counterbalanced Evaluation
```bash
python src/run_ad_series.py --txt o2_results_ad_series.txt --json o2_results_ad_series.json
```

---

## 🔬 Core Features

> **Executive Narrative**: This toolkit is an empirical research initiative. It quantifies how autonomous AI agents fail due to poor or conflicting documentation, and maps the exact neural circuitry open-weights LLMs (specifically Google's Gemma 4-e4b) use to resolve information conflicts.


* **Jacobian Matrices**: The precomputed Jacobian matrices (`jacobians_google_gemma-4-e4b.pt`) are included in the `data/` directory. If you need to regenerate this file locally, you can run `fit_j_lens.py`. For security, always load this tensor file using `torch.load(..., weights_only=True)`.

* **Jacobian Lens (J-Lens) Probing**: Project hidden residual stream activations $h_\ell$ through the Jacobian matrix $J_\ell = \mathbb{E}\left[\frac{\partial h_{\text{final}}}{\partial h_\ell}\right]$ to inspect unspoken intermediate representations in the Global Workspace.
* **Activation Patching**: Perform causal interventions on intermediate layer activations to verify trust circuit mechanisms.
* **Counterbalanced Evaluation**: TOST-validated evaluation of authority vs. position bias across 10 prompt conditions.

---

## 📄 License

Distributed under the Apache 2.0 License. See `LICENSE` for details.
