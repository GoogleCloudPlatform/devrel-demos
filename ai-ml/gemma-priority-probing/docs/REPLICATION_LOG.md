# Gemma Evaluation: AD-Series Replication Log

**Experiment Title**: Behavioral Probing of Authority vs. Recency Bias in gemma-4-e4b (AD-Series)
**Run Date**: July 29, 2026
**Write Date**: July 30, 2026
**Primary Investigators**: Gemma Research Team  
**Project Directory**: `gemma_eval_words_speak_louder_than_order`  

---

## 1. Executive Summary & AD-Series Results

We have empirically investigated how the **gemma-4-e4b** model resolves conflicting information using a 13-item analysis suite (n=13). Our primary finding from the definitive AD-series is that **Semantic source framing dominates positional bias**.

### Key Empirical Results:
1. **Source Priority Dominates Positional Bias**:
   * When context blocks carry genuine authority/recency semantics (e.g., "Official Guideline" vs "Team Update"), the model overwhelmingly favors the recent source. Semantics outweighs position by a factor of roughly **4:1**.
   * In the cue-free loaded condition (T5b), the Source-Framing effect is **+1.054 nats**, compared to a Serial position magnitude of **−0.265 nats** (CI excludes zero — primacy is still present, but outweighed).
   * Note: Source-Framing is a **header+body package** (aliased by design), not a header-only effect.
2. **Primacy is present but magnitude-fragile**:
   * The Serial Position Effect is negative in mean (indicating primacy) and the CI excludes zero in **10/10** tested conditions. TOST rejects equivalence in **10/10** conditions.
   * However, its magnitude is not stable, ranging from -0.172 to -0.884 nats (a 5.1x swing driven entirely by surface framing).
3. **Induction Head Claim Retracted & Replaced**:
   * The earlier AA-series attributed primacy to induction/copy heads keyed on a repeated "is {e}" trigram. 
   * With cue count varied while body wording is held constant, the arms disagree: A1 = -0.400 (neutral) vs A2 = +0.110 ns (authority) — opposite signs. The pooled estimate A3 = -0.145 [-0.290, +0.010] covers zero and is outlier-policy dependent (-0.166* at n=14, where CI excludes zero). 
   * The induction claim is therefore *unsupported* and formally retracted.
   * **B4 = +0.250 [+0.010, +0.522]**: Variation reduces primacy at 0 cues. Verbatim cross-block repetition replaced the induction story. This is a surface-level behavioral regularity; a circuit-level claim requires activation patching over the block-1/block-2 residual stream. The strongest primacy in the study is **T1c = −0.884 (13/13 items)**, which is completely cue-free but fully verbatim.
4. **Header × Body Interaction & Null-Control Failures**:
   * **C3 = −0.162 [−0.303, −0.034]**: Cue-free header × body interaction (C1 = +0.153 ns, C2 = +0.315* — both positive). Authority *reduces* primacy in both body regimes; the interaction is a magnitude difference, not a reversal. AC's +0.347 (C5) is superseded as cue-asymmetric.
   * **E1 = +0.216 [−0.004, +0.364]**: Unresolved, trending suppression, opposite to the retracted AB claim. (Outlier-policy dependent: +0.237, [+0.025, +0.375] at n=14).
   * **Null-control failures**: Order fails in T2; Role fails in T1, T2, T2c, T3 (−0.159, largest), T3c.

---

## 2. Environment & System Setup

* **OS**: macOS-15.7.7-arm64
* **Model Evaluated**: `google/gemma-4-e4b`
* **Device / Env**: `torch 2.13.0, fp32, eval mode, no sampling`, `python 3.12.13` (using `venv_torch` instead of `./venv` for J-Lens toolkit compatibility), `transformers 5.14.1`, `numpy 2.5.1`, `scipy 1.18.0`

---

## 3. Artifacts & Benchmark Seed

- **Project Location**: `gemma_eval_words_speak_louder_than_order`
- **AD-Series Dataset**: 15 inline single-token candidate pairs (14 kept; `Queue/Roster` rejected). Global keep set n=13, `Spec/Brief` dropped (T5b Order = 0.602). 
  - **Outlier Rule**: `|Token| > 2.0 or |Order| > 0.5; GLOBAL keep set = intersection across all 10 conditions`.
  - Results evaluated under dual primary (n=13) and sensitivity (n=14) policies.
- **AD-Series Results**: `data/results/o2_results_ad_series_FINAL.json` and `data/results/o2_results_ad_series_FINAL.txt` (real source file, not a transcript splice (AD5)). Cue-count assertion PASSED 10/10. (Note: `o2_results_ac_series.txt/.json` are superseded).

---

## 4. Execution Journal

- End-to-end execution of `run_ad_series.py` across 784 forward passes.
- Calculated BCa bootstrap 95% CIs with 9,999 resamples.
- Found the initial induction hypothesis to be unsupported, discovering that semantic framing dominates position.

---

## 5. Retractions

* **AA-series (Induction Claim)**: Retracted. Overturned by the AD contrast A3, which showed opposite-signed effects across header arms and an unsupported pooled estimate.
* **AB-series (Amplification Claim)**: Retracted. The retraction rests on the AB design confound; E1 is directionally corroborating but covers zero under the primary policy and does not independently falsify the claim.
* **AC-series (Header×Body Interaction)**: Superseded. C5 paired a cue-free arm (C1) against a 2-cue arm (C4); the cue-matched estimate is C3 = −0.162 [−0.303, −0.034].
* **Z-series (Positional Override Claim)**: Retracted. Falsified by T5b, where semantic source framing outweighs positional bias roughly 4:1.

## 6. Limitations and non-claims

- **Framing is a header+body package.** T5/T5b alias source semantics with body wording by construction. The 4:1 comparison therefore contrasts a *compound* manipulation against a *pure positional* one, and indexes relative manipulation strength as much as model bias. The **direction** is solid; the ratio is a descriptive point estimate with no interval and should not be quoted as a model constant.
- **Single model, single question stem, single-token answers, n=13.** No cross-model or cross-domain generalization is claimed.
- **Outlier-policy sensitivity.** The pooled cue effect flips CI-significance between the primary (n=13, covers zero) and sensitivity (n=14, A3 = −0.166 [−0.306, −0.011]*) policies. The AA retraction holds under both, but the *reason* differs (unsupported vs. refuted). Both are reported.
- **No mechanistic claim.** Circuit-level attribution requires activation patching over the block-1/block-2 residual stream. Phase 3 J-space results are quarantined (probes flat at 0.0 for L0–24) and are **not** part of this paper.
