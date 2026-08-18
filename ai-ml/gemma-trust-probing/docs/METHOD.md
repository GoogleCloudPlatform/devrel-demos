# Technical Method: Logit Lens & Jacobian Lens (J-Lens)

This document formalizes the mathematical framework and layer-wise representation probing methodology used in this toolkit.

---

## 1. Literature & Theoretical Foundation

Probing intermediate residual streams in Transformer models builds on the **Logit Lens** paradigm and its expansion via **Jacobian / J-Lens** transformations:

- **Anthropic Transformer Circuits Publication (July 6, 2026)**:  
  [https://transformer-circuits.pub/2026/workspace](https://transformer-circuits.pub/2026/workspace)
- **Logit Lens Foundations**: Nostalgebraist (2020), *interpreting residual streams via unembedding projections*.

---

## 2. Mathematical Formulations

Given a Transformer model with $L$ hidden layers, residual stream activation vector $h_\ell \in \mathbb{R}^{d_{\text{model}}}$ at layer $\ell \in [0, L-1]$, layer normalization $\text{norm}(\cdot)$, and vocabulary unembedding matrix $W_U \in \mathbb{R}^{|V| \times d_{\text{model}}}$:

### 2.1 Traditional Logit Lens
The traditional Logit Lens projects the normalized intermediate state $h_\ell$ directly into vocabulary logit space:

$$P_{\text{logit}}(\ell) = \text{softmax}\left( W_U \cdot \text{norm}(h_\ell) \right)$$

### 2.2 Jacobian Lens (J-Lens)
The Jacobian Lens models the linear derivative transformation mapping intermediate activations $h_\ell$ to the final residual layer state before output generation. 

Crucially, as outlined by Gurnee et al., this Jacobian matrix must be computed as an **expectation over a corpus of prompts**, as well as averaged over source position $t$ and all subsequent positions $t' \geq t$. This distinguishes representations that are structurally verbalizable from those that merely happen to be verbalized in one particular context:

$$J_\ell = \mathbb{E}_{\,t,\;t' \geq t,\;\text{prompt}} \left[ \frac{\partial h_{\text{final},t'}}{\partial h_{\ell,t}} \right]$$

$$P_{\text{J-Lens}}(\ell) = \text{softmax}\left( W_U \cdot \text{norm}(J_\ell \cdot h_\ell) \right)$$

*Note: The traditional Logit Lens is the special case where $J_\ell = I$. If the Jacobian matrix is not empirically fitted and applied, the method collapses to a Logit Lens.*

---

## 3. Structural Depth Priors vs. Empirical Measurement

- **Heuristic Window Prior (`window_prior`)**:  
  By default, intermediate layers between $0.38 \times L$ and $0.92 \times L$ are designated as a structural prior hypothesis (`DEFAULT_WINDOW_PRIOR_FRAC`).
- **Empirical Measurement (`window_measured`)**:  
  Empirical causal windows are determined exclusively through token-aligned single-layer $\times$ position ($L \times P$) activation patching sweeps.


## Visualization
`visualize_j_space.py` is the sole supported visualization path for J-Lens trajectory analysis. The legacy web inspector has been deprecated and removed.
