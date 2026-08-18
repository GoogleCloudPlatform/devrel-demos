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
run_ad_series.py — Project Lantern AD-Series (FINAL)
=====================================================
Fixes AD1 (cue ladder confounded cue-removal with wording-variation),
     AD2 (interaction arms had asymmetric cue counts: (T4c-T2c)-(T3-T1)),
     AD3 (source-framing effect buried beneath primacy),
     AD5 (10 of 14 valid pairs used; script was a transcript splice).
     (Note: AD4 was a reporting limitation regarding null-failures, not a code defect).

A "cue" = the entity immediately following "is"/"is now" -- the local trigram an
induction/copy head can key on when the construction recurs in both blocks.
W2/W3/Y1b/Y2b place {e} sentence-initially, so its left-context is "\\n".

The AC ladder (T1: 2 cues verbatim -> T2: 1 cue mixed -> T2c: 0 cues mixed) varied
cue-count AND body-variation together. AD adds verbatim cue-free cells so cue-count
varies alone:
    PURE CUE CONTRAST (variation fixed = verbatim):  T1c - T1,  T3c - T3
    FULLY CUE-FREE INTERACTION (all arms 0 cues):    (T4c - T2c) - (T3c - T1c)

Contrast algebra (identical orientation in every cell)
------------------------------------------------------
e_i = log P(B) - log P(A) at the final position.
  Q1 stale-role block FIRST,  stale=A recent=B
  Q2 recent-role block FIRST, stale=A recent=B
  Q3 stale-role block FIRST,  stale=B recent=A
  Q4 recent-role block FIRST, stale=B recent=A

  Token  = (e1+e2+e3+e4)/4   base preference for B over A
  Role   = (e1+e2-e3-e4)/4   recent-role effect (T5/T5b: source-framing, body-aliased)
  Order  = (e1-e2+e3-e4)/4   NULL CONTROL
  Serial = (e1-e2-e3+e4)/4   + recency / - primacy   [HALF-EFFECT; full swing = 2x]

Outlier policy
--------------
Per-condition flags: |Token| > 2.0, |Order| > 0.50.
GLOBAL KEEP SET = intersection of unflagged items across ALL TEN conditions.
Every aggregate and every contrast uses that identical index set. One n.
A sensitivity re-run on the full unfiltered set is printed at the end.
"""

import argparse
import datetime
import json
import platform
import sys

import numpy as np
import scipy
import torch
import transformers
from scipy import stats
from transformers import AutoTokenizer, AutoModelForCausalLM

# ------------------------------------------------------------------ configuration
MODEL_ID = "google/gemma-4-e4b"
SEED = 42
N_RESAMPLES = 9999
TOST_BOUND = 0.15
OUTLIER_TOKEN = 2.0
OUTLIER_ORDER = 0.50

import os
DEFAULT_TXT = os.environ.get("OUTPUT_TXT", "./o2_results_ad_series_FINAL.txt")
DEFAULT_JSON = os.environ.get("OUTPUT_JSON", "./o2_results_ad_series_FINAL.json")

QUESTION = "Question: What template should I use for project planning?\nAnswer:"

# --- Role-NEUTRAL bodies --------------------------------------------------------
W1 = "The recommended template for project planning is {e}."          # CUE
W2 = "{e} is the template we use for project planning."               # cue-free
W3 = "{e} remains our standard project planning template."            # cue-free

# --- Role-LOADED bodies (body IS the manipulation) ------------------------------
Y1 = ("Official guidelines state that for Project Planning Template, "
      "the required configuration is {e}.")                            # CUE
Y2 = ("Update: The new updated specification for Project Planning Template "
      "is now {e}.")                                                   # CUE
Y1b = ("{e} is the required configuration for Project Planning Template, "
       "per official guidelines.")                                     # cue-free
Y2b = ("{e} is the newly updated specification for Project Planning Template, "
       "effective now.")                                               # cue-free

H_NEUTRAL = ("Memo Kestrel", "Memo Larkin")                  # (stale-role, recent-role)
H_AUTHORITY = ("OFFICIAL GUIDELINE (2019)", "Team Update (Yesterday)")

CANDIDATES = [
    (" Scrum", " Kanban"), (" Agile", " Waterfall"), (" Roadmap", " Milestone"),
    (" Spec", " Brief"), (" Scope", " Scale"), (" Phase", " Stage"),
    (" Cycle", " Sprint"), (" Board", " Grid"), (" Matrix", " Table"),
    (" Guide", " Manual"), (" Index", " Log"), (" Deck", " Pitch"),
    (" Queue", " Roster"), (" Plan", " Draft"), (" Chart", " Graph"),
]

ROLE_NEUTRAL_LABEL = "Role-Framing Effect [NULL]"
ROLE_LOADED_LABEL = "Source-Framing (header+body)"

# key, name, headers, wordings, role_bound, cues, variation, role_label, note
CONDITIONS = [
    ("T1", "Neutral x Verbatim (W1,W1)", H_NEUTRAL, [(W1, W1)], False, 2, "verbatim",
     ROLE_NEUTRAL_LABEL,
     "Degenerate control: blocks identical but for one token. Nulls near-forced."),
    ("T1c", "Neutral x Verbatim CUE-FREE (W2,W2)", H_NEUTRAL, [(W2, W2)], False, 0,
     "verbatim", ROLE_NEUTRAL_LABEL,
     "NEW (AD1). Paired with T1 this isolates the copy cue with variation held fixed."),
    ("T2", "Neutral x Mixed (W1,W2)", H_NEUTRAL, [(W1, W2), (W2, W1)], False, 1,
     "mixed", ROLE_NEUTRAL_LABEL, None),
    ("T2c", "Neutral x Mixed CUE-FREE (W2,W3)", H_NEUTRAL, [(W2, W3), (W3, W2)], False,
     0, "mixed", ROLE_NEUTRAL_LABEL, None),
    ("T3", "Authority x Verbatim (W1,W1)", H_AUTHORITY, [(W1, W1)], False, 2,
     "verbatim", ROLE_NEUTRAL_LABEL, None),
    ("T3c", "Authority x Verbatim CUE-FREE (W2,W2)", H_AUTHORITY, [(W2, W2)], False, 0,
     "verbatim", ROLE_NEUTRAL_LABEL,
     "NEW (AD2). Supplies the cue-free verbatim arm of the interaction."),
    ("T4", "Authority x Mixed (W1,W2)", H_AUTHORITY, [(W1, W2), (W2, W1)], False, 1,
     "mixed", ROLE_NEUTRAL_LABEL, None),
    ("T4c", "Authority x Mixed CUE-FREE (W2,W3)", H_AUTHORITY, [(W2, W3), (W3, W2)],
     False, 0, "mixed", ROLE_NEUTRAL_LABEL, "Cue-matched baseline for T5b."),
    ("T5", "Authority x LOADED (Y1,Y2)", H_AUTHORITY, [(Y1, Y2)], True, 2, "loaded",
     ROLE_LOADED_LABEL,
     "role_bound: NOT counterbalanced (AB1). Body IS the manipulation; 'Role' is "
     "aliased with body wording by construction."),
    ("T5b", "Authority x LOADED CUE-FREE (Y1b,Y2b)", H_AUTHORITY, [(Y1b, Y2b)], True,
     0, "loaded", ROLE_LOADED_LABEL, "Head-to-head cell. Compare only against T4c."),
]


# ------------------------------------------------------------------------ logging
class Log:
    """Single writer: everything printed is also buffered. No orphan print() calls."""

    def __init__(self):
        self.lines = []

    def __call__(self, s=""):
        print(s, flush=True)
        self.lines.append(s)

    def save(self, path):
        with open(path, "w") as f:
            f.write("\n".join(self.lines) + "\n")
        print(f"\n[log written to {path}]", flush=True)


# -------------------------------------------------------------------------- setup
def build_valid_pairs(tok, n_target=None):
    """MANDATORY single-token filter (Y1 regression guard). n_target=None -> keep all."""
    kept, rejected = [], []
    for a, b in CANDIDATES:
        ia = tok.encode(a, add_special_tokens=False)
        ib = tok.encode(b, add_special_tokens=False)
        if len(ia) == 1 and len(ib) == 1:
            if n_target is None or len(kept) < n_target:
                kept.append((a.strip(), b.strip(), ia[0], ib[0]))
        else:
            rejected.append((a.strip(), b.strip(), len(ia), len(ib)))
    return kept, rejected


def build_prompt(h1, body1, e1, h2, body2, e2):
    return (f"Context:\n[{h1}]\n{body1.format(e=e1)}\n\n"
            f"[{h2}]\n{body2.format(e=e2)}\n\n{QUESTION}")


def count_cues(wordings):
    bx, by = wordings[0]
    return sum(1 for b in (bx, by) if ("is {e}" in b) or ("is now {e}" in b))


def log_diff(model, tok, prompt, id_a, id_b):
    inputs = tok(prompt, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits[0, -1, :].float()
    logp = torch.log_softmax(logits, dim=-1)
    return (logp[id_b] - logp[id_a]).item()


# --------------------------------------------------------------------- evaluation
def evaluate_condition(model, tok, pairs, headers, wordings, role_bound, key, log):
    """
    role_bound=False -> (body_FIRST_block, body_SECOND_block). Either ONE assignment
                        with both bodies identical ("verbatim"), or TWO that are
                        proper swaps of the same pair ("mixed").
    role_bound=True  -> (body_STALE_role, body_RECENT_role); EXACTLY ONE assignment.
                        Counterbalancing here averages the semantic manipulation to
                        zero (the AB1 bug). Enforced below.
    """
    if role_bound:
        if len(wordings) != 1:
            raise ValueError(
                f"[{key}] role_bound=True requires exactly one wording assignment; got "
                f"{len(wordings)}. Counterbalancing cancels the manipulation (AB1).")
    else:
        if len(wordings) == 2:
            (a1, b1), (a2, b2) = wordings
            if not (a1 == b2 and b1 == a2):
                raise ValueError(f"[{key}] two-wording role_bound=False set is not a "
                                 f"proper counterbalance of the same two bodies.")
        elif len(wordings) == 1:
            a1, b1 = wordings[0]
            if a1 != b1:
                raise ValueError(f"[{key}] single-wording role_bound=False cell must "
                                 f"use the same body in both blocks (verbatim).")
        else:
            raise ValueError(f"[{key}] role_bound=False needs 1 or 2 wordings.")

    h_stale, h_recent = headers
    effects, cells, n_passes = [], [], 0

    for A, B, idA, idB in pairs:
        acc = np.zeros(4)
        for bx, by in wordings:
            if role_bound:
                b_stale, b_recent = bx, by
                f1, s1 = b_stale, b_recent      # Q1/Q3: stale block first
                f2, s2 = b_recent, b_stale      # Q2/Q4: recent block first
            else:
                f1, s1 = bx, by
                f2, s2 = bx, by

            e1 = log_diff(model, tok, build_prompt(h_stale,  f1, A, h_recent, s1, B), idA, idB)
            e2 = log_diff(model, tok, build_prompt(h_recent, f2, B, h_stale,  s2, A), idA, idB)
            e3 = log_diff(model, tok, build_prompt(h_stale,  f1, B, h_recent, s1, A), idA, idB)
            e4 = log_diff(model, tok, build_prompt(h_recent, f2, A, h_stale,  s2, B), idA, idB)
            acc += np.array([e1, e2, e3, e4])
            n_passes += 4

        c1, c2, c3, c4 = acc / len(wordings)
        effects.append([(c1 + c2 + c3 + c4) / 4,      # Token
                        (c1 + c2 - c3 - c4) / 4,      # Role / Source-Framing
                        (c1 - c2 + c3 - c4) / 4,      # Order  [NULL]
                        (c1 - c2 - c3 + c4) / 4])     # Serial [- = primacy]
        cells.append([c1, c2, c3, c4])

    log(f"  [{key}] {n_passes} forward passes complete.")
    return np.array(effects), np.array(cells), n_passes


def sample_prompt(headers, wordings, pair):
    A, B, _, _ = pair
    bx, by = wordings[0]
    return build_prompt(headers[0], bx, A, headers[1], by, B)


# --------------------------------------------------------------------- statistics
def bca(x, cl=0.95):
    x = np.asarray(x, dtype=float)
    if len(x) < 3 or np.var(x) == 0:
        m = float(np.mean(x))
        return m, m
    try:
        r = stats.bootstrap((x,), np.mean, method="bca", confidence_level=cl,
                            n_resamples=N_RESAMPLES, random_state=SEED)
    except Exception:
        r = stats.bootstrap((x,), np.mean, method="percentile", confidence_level=cl,
                            n_resamples=N_RESAMPLES, random_state=SEED)
    return float(r.confidence_interval.low), float(r.confidence_interval.high)


def fmt(x, label, cl=0.95):
    lo, hi = bca(x, cl)
    flag = "" if (lo <= 0 <= hi) else "  *"
    return f"{label:<46} {np.mean(x):+7.3f}  [{lo:+.3f}, {hi:+.3f}]{flag}"


def tost(x, bound=TOST_BOUND):
    x = np.asarray(x, dtype=float)
    n = len(x)
    se = np.std(x, ddof=1) / np.sqrt(n)
    p = max(stats.t.sf((np.mean(x) + bound) / se, df=n - 1),
            stats.t.cdf((np.mean(x) - bound) / se, df=n - 1))
    lo90, hi90 = bca(x, cl=0.90)
    return p, (lo90, hi90), bool(p < 0.05 and -bound <= lo90 and hi90 <= bound)


def flag_outliers(effects):
    return [i for i in range(len(effects))
            if abs(effects[i, 0]) > OUTLIER_TOKEN or abs(effects[i, 2]) > OUTLIER_ORDER]


def contrast(vec, label, log, store, cl=0.95):
    """BCa CI on a per-item contrast vector already restricted to the keep set."""
    v = np.asarray(vec, dtype=float)
    lo, hi = bca(v, cl)
    flag = "" if (lo <= 0 <= hi) else "  *"
    log(f"{label:<56} {np.mean(v):+7.3f}  [{lo:+.3f}, {hi:+.3f}]{flag}   "
        f"(SD={np.std(v, ddof=1):.3f}, n={len(v)})")
    store[label] = {"mean": float(np.mean(v)), "ci_lo": lo, "ci_hi": hi,
                    "sd": float(np.std(v, ddof=1)), "n": int(len(v))}
    return v


def paired(a, b, label, log, store, cl=0.95):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    assert a.shape == b.shape, f"{label}: shape mismatch {a.shape} vs {b.shape}"
    return contrast(a - b, label, log, store, cl)


# ------------------------------------------------------------------------- report
def report(key, name, effects, cells, pairs, keep, log, role_label, cues, note=None):
    """`keep` is the GLOBAL index set. Aggregates use it verbatim (AC2)."""
    log("")
    log("=" * 92)
    log(f"=== {key}: {name}   [{cues} 'is {{e}}' cue(s) per prompt]")
    log("=" * 92)
    if note:
        log(f"NOTE: {note}")

    log("")
    log("Per-item raw cells (e1..e4) and derived effects   ['X' = dropped by global policy]:")
    log(f"{'':2}{'item':<20}{'e1':>9}{'e2':>9}{'e3':>9}{'e4':>9} | "
        f"{'Token':>8}{'Role':>9}{'Order':>8}{'Serial':>9}")
    log("-" * 92)
    local_bad = flag_outliers(effects)
    for i, (A, B, _, _) in enumerate(pairs):
        c, e = cells[i], effects[i]
        mark = " " if i in keep else "X"
        log(f"{mark} {A + '/' + B:<20}{c[0]:>9.3f}{c[1]:>9.3f}{c[2]:>9.3f}{c[3]:>9.3f} | "
            f"{e[0]:>8.3f}{e[1]:>9.3f}{e[2]:>8.3f}{e[3]:>9.3f}")

    if local_bad:
        log(f"\nLocally flagged in {key} ({len(local_bad)}): "
            f"{[pairs[i][0] + '/' + pairs[i][1] for i in local_bad]}")
    else:
        log(f"\nLocally flagged in {key}: none.")

    clean = effects[keep]
    log(f"\nAggregates over the GLOBAL keep set (n={len(keep)}), BCa 95% CI, "
        f"{N_RESAMPLES} resamples, seed={SEED}; '*' = CI excludes 0:")
    log(fmt(clean[:, 0], "Token Effect (base rate)"))
    log(fmt(clean[:, 1], role_label))
    log(fmt(clean[:, 2], "Block-Order Effect [NULL CONTROL]"))
    log(fmt(clean[:, 3], "Serial Position Effect (HALF-effect)"))

    olo, ohi = bca(clean[:, 2])
    log(f"  -> Order null {'PASSES' if olo <= 0 <= ohi else 'FAILS'}.")
    if role_label != ROLE_LOADED_LABEL:
        rlo, rhi = bca(clean[:, 1])
        log(f"  -> Role null {'PASSES' if rlo <= 0 <= rhi else 'FAILS'}.")
    else:
        log("  -> Role is the MANIPULATION here (aliased with body); no null expected.")

    ser = clean[:, 3]
    log(f"  -> Full first-vs-last swing = {2 * np.mean(ser):+.3f} nats.")
    log(f"  -> Sign consistency: {int(np.sum(ser < 0))}/{len(ser)} items negative (primacy).")
    p, ci90, eq = tost(ser)
    log(f"  -> TOST vs +/-{TOST_BOUND}: equivalent={eq} (p={p:.4f}, 90% CI "
        f"[{ci90[0]:+.3f}, {ci90[1]:+.3f}]). Non-rejection != equality.")
    return {"serial": ser, "role": clean[:, 1], "order": clean[:, 2], "token": clean[:, 0]}


# ------------------------------------------------------------------- contrast set
def slice_S(all_effects, keep):
    """Build {key: {serial, role, order, token}} restricted to an index set."""
    S = {}
    for key, eff in all_effects.items():
        c = eff[keep]
        S[key] = {"token": c[:, 0], "role": c[:, 1], "order": c[:, 2], "serial": c[:, 3]}
    return S


def run_contrasts(S, log, store, tag):
    log("")
    log("=" * 92)
    log(f"=== PRE-REGISTERED CONTRASTS  ({tag})")
    log("=" * 92)
    ser = {k: v["serial"] for k, v in S.items()}
    role = {k: v["role"] for k, v in S.items()}
    n = len(ser["T1"])

    log("\n--- A. PURE CUE EFFECT (AD1): body-variation held constant at 'verbatim' ---")
    log("    Positive => removing the cue REDUCES primacy => induction contributes.")
    log("    Zero/negative => retract the AA-series induction claim.")
    a1 = paired(ser["T1c"], ser["T1"], "A1  Neutral   cue removal   (T1c - T1)", log, store)
    a2 = paired(ser["T3c"], ser["T3"], "A2  Authority cue removal   (T3c - T3)", log, store)
    pooled = (a1 + a2) / 2.0
    contrast(pooled, "A3  Pooled pure cue effect  (mean of A1,A2)", log, store)
    plo, phi = bca(pooled)
    if phi < 0:
        verdict = "CUE REMOVAL INCREASES PRIMACY -> induction claim REFUTED (retract AA)."
    elif plo > 0:
        verdict = "CUE REMOVAL REDUCES PRIMACY -> induction contribution SUPPORTED."
    else:
        verdict = "CI covers zero -> NO detectable cue contribution; AA claim UNSUPPORTED."
    log(f"    VERDICT: {verdict}")

    # A4: do the two arms actually agree? (heterogeneity test for the pooling in A3)
    contrast(a1 - a2, "A4  arm heterogeneity      (A1 - A2)", log, store)
    hlo, hhi = bca(a1 - a2)
    if not (hlo <= 0 <= hhi):
        log("    WARNING: A1 and A2 differ significantly. A3 pools heterogeneous arms; "
            "report A1 and A2 separately and treat A3 as descriptive only.")

    log("\n--- B. CUE LADDER, neutral headers (cue-count AND variation both move) ---")
    log("    Monotonic |Serial| decrease as cues drop => induction story. AC found it "
        "NON-monotonic.")
    for k in ("T1", "T2", "T2c", "T1c"):
        lo, hi = bca(ser[k])
        log(f"    {k:<4} serial = {np.mean(ser[k]):+7.3f}  [{lo:+.3f}, {hi:+.3f}]")
    paired(ser["T2"],  ser["T1"],  "B1  2 cues -> 1 cue          (T2  - T1)", log, store)
    paired(ser["T2c"], ser["T2"],  "B2  1 cue  -> 0 cues         (T2c - T2)", log, store)
    paired(ser["T2c"], ser["T1"],  "B3  net ladder              (T2c - T1)", log, store)
    paired(ser["T2c"], ser["T1c"], "B4  variation effect @0 cues (T2c - T1c)", log, store)
    lad = [np.mean(ser["T1"]), np.mean(ser["T2"]), np.mean(ser["T2c"])]
    mono = (lad[0] <= lad[1] <= lad[2]) or (lad[0] >= lad[1] >= lad[2])
    log(f"    Ladder monotonic in mean: {mono}   ({lad[0]:+.3f} -> {lad[1]:+.3f} "
        f"-> {lad[2]:+.3f})")

    log("\n--- C. HEADER x BODY INTERACTION (AD2): all four arms cue-matched ---")
    se_mixed = paired(ser["T4c"], ser["T2c"],
                      "C1  simple effect, mixed  (T4c - T2c)", log, store)
    se_verb = paired(ser["T3c"], ser["T1c"],
                     "C2  simple effect, verbatim (T3c - T1c)", log, store)
    contrast(se_mixed - se_verb,
             "C3  FULLY CUE-FREE INTERACTION  (C1 - C2)", log, store)
    log("    Legacy/contaminated comparators (report only, do not headline):")
    se_v_cued = paired(ser["T3"], ser["T1"], "C4  simple effect, verbatim 2-cue (T3 - T1)",
                       log, store)
    contrast(se_mixed - se_v_cued,
             "C5  AC-style asymmetric interaction (C1 - C4)", log, store)
    paired(ser["T4"], ser["T2"], "C6  simple effect, 1-cue mixed (T4 - T2)", log, store)
    ilo, ihi = bca(se_mixed - se_verb)
    log(f"    Interaction {'SURVIVES' if not (ilo <= 0 <= ihi) else 'DOES NOT SURVIVE'} "
        f"full cue-matching.")

    log("\n--- D. SOURCE-FRAMING vs POSITION (AD3): the largest effect in the study ---")
    for k in ("T5", "T5b"):
        rlo, rhi = bca(role[k])
        slo, shi = bca(ser[k])
        log(f"    {k:<4} Source-Framing = {np.mean(role[k]):+7.3f} [{rlo:+.3f}, {rhi:+.3f}]"
            f"   |Serial| = {abs(np.mean(ser[k])):+7.3f} [{slo:+.3f}, {shi:+.3f}]")
    d1 = contrast(np.abs(role["T5b"]) - np.abs(ser["T5b"]),
                  "D1  |Source-Framing| - |Serial|, T5b (cue-free)", log, store)
    contrast(np.abs(role["T5"]) - np.abs(ser["T5"]),
             "D2  |Source-Framing| - |Serial|, T5  (cued)", log, store)
    paired(role["T5b"], role["T5"], "D3  cue removal on framing  (T5b - T5 Role)", log, store)
    if np.mean(np.abs(ser["T5b"])) > 1e-9:
        log(f"    Ratio |Framing|/|Serial| in T5b = "
            f"{np.mean(np.abs(role['T5b'])) / np.mean(np.abs(ser['T5b'])):.2f}x")
    dlo, dhi = bca(d1)
    log(f"    VERDICT: semantics {'DOMINATES' if dlo > 0 else ('is DOMINATED BY' if dhi < 0 else 'is NOT distinguishable from')} position.")

    log("\n--- E. SEMANTIC SUPPRESSION (the only cue-matched test) ---")
    e1v = paired(ser["T5b"], ser["T4c"], "E1  T5b - T4c  [PRE-REGISTERED]", log, store)
    paired(ser["T5"], ser["T4"], "E2  T5 - T4    [confounded, reference only]", log, store)
    elo, ehi = bca(e1v)
    if elo > 0:
        ev = "semantic conflict SUPPRESSES primacy."
    elif ehi < 0:
        ev = "semantic conflict AMPLIFIES primacy."
    else:
        ev = "UNRESOLVED (CI covers 0). Publish primacy alone; make no suppression claim."
    log(f"    VERDICT: {ev}")

    log("\n--- F. PRIMACY ROBUSTNESS ACROSS ALL TEN CELLS (AD3 magnitude fragility) ---")
    log(f"    {'cell':<6}{'cues':>5}{'serial':>10}{'CI_lo':>9}{'CI_hi':>9}"
        f"{'neg/n':>9}{'full swing':>12}")
    rows = []
    for key, name, _, w, rb, cues, var, _, _ in CONDITIONS:
        v = ser[key]
        lo, hi = bca(v)
        log(f"    {key:<6}{cues:>5}{np.mean(v):>10.3f}{lo:>9.3f}{hi:>9.3f}"
            f"{int(np.sum(v < 0)):>6}/{len(v):<3}{2 * np.mean(v):>12.3f}")
        rows.append((key, float(np.mean(v)), lo, hi))
        store[f"F  serial {key}"] = {"mean": float(np.mean(v)), "ci_lo": lo, "ci_hi": hi,
                                     "cues": cues, "variation": var, "n": len(v)}
    mags = [abs(r[1]) for r in rows]
    log(f"    Range: {min(mags):.3f} to {max(mags):.3f} nats "
        f"({max(mags) / max(min(mags), 1e-9):.1f}x swing across framings).")
    log(f"    Cells with CI excluding zero: "
        f"{sum(1 for _, _, lo, hi in rows if not (lo <= 0 <= hi))}/{len(rows)}.")
    log(f"    Cells negative in mean: {sum(1 for _, m, _, _ in rows if m < 0)}/{len(rows)}.")
    log(f"    n per contrast = {n}")

    # G: consolidated null-control audit (paper Sec. 'Control diagnostics')
    log("\n--- G. NULL-CONTROL AUDIT ---")
    log(f"    {'cell':<6}{'Order':>9}{'ok':>5}{'Role':>10}{'ok':>5}")
    for key, *_ , rlabel, _ in CONDITIONS:
        o, r = S[key]["order"], S[key]["role"]
        olo, ohi = bca(o); rlo, rhi = bca(r)
        role_ok = "n/a" if rlabel == ROLE_LOADED_LABEL else ("PASS" if rlo <= 0 <= rhi else "FAIL")
        log(f"    {key:<6}{np.mean(o):>9.3f}{'PASS' if olo <= 0 <= ohi else 'FAIL':>5}"
            f"{np.mean(r):>10.3f}{role_ok:>5}")

    return store


# ---------------------------------------------------------------------------- run
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_TXT)
    ap.add_argument("--json", default=DEFAULT_JSON)
    ap.add_argument("--n-pairs", type=int, default=None,
                    help="Cap on single-token pairs. Default None = use all 14 (AD5).")
    args = ap.parse_args()

    torch.manual_seed(SEED)
    np.random.seed(SEED)

    log = Log()

    # ------------------------------------------------------------ provenance (AC6)
    log("=" * 92)
    log("PROJECT LANTERN — AD-SERIES  (cue-matched, 10 cells, full pair set)")
    log("=" * 92)
    log(f"timestamp     : {datetime.datetime.now().astimezone().isoformat(timespec='seconds')}")
    log(f"model         : {MODEL_ID}    dtype=float32    eval mode, no sampling")
    log(f"seed          : {SEED}        BCa resamples: {N_RESAMPLES}")
    log(f"python        : {sys.version.split()[0]}")
    log(f"torch         : {torch.__version__}   transformers: {transformers.__version__}")
    log(f"numpy         : {np.__version__}      scipy: {scipy.__version__}")
    log(f"platform      : {platform.platform()}")
    log(f"outlier rule  : |Token|>{OUTLIER_TOKEN} or |Order|>{OUTLIER_ORDER}; "
        f"GLOBAL keep set = intersection across all 10 conditions")
    log("NOTE          : Serial/Role/Order are HALF-EFFECTS. Full swing = 2 x Serial.")
    log("NOTE          : This file is a real source file, not a transcript splice (AD5).")

    # cue-count integrity check
    for key, _, _, w, _, cues, _, _, _ in CONDITIONS:
        assert count_cues(w) == cues, (
            f"[{key}] declared {cues} cues but bodies contain {count_cues(w)}. "
            f"Cue ladder invalid — fix the body strings or the declaration.")
    log("Cue-count assertion: PASSED for all 10 conditions.")

    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    pairs, rejected = build_valid_pairs(tok, args.n_pairs)
    log(f"\nSingle-token filter: kept {len(pairs)} of {len(CANDIDATES)}, "
        f"rejected {len(rejected)}.")
    log(f"  kept     : {[a + '/' + b for a, b, _, _ in pairs]}")
    log(f"  rejected : {[(a + '/' + b, na, nb) for a, b, na, nb in rejected]}")
    if len(pairs) < 4:
        raise SystemExit("Too few single-token pairs; aborting.")

    total = sum(4 * len(w) * len(pairs) for _, _, _, w, _, _, _, _, _ in CONDITIONS)
    log(f"\nPlanned forward passes: {total} across {len(CONDITIONS)} conditions.")

    log("\n" + "-" * 92)
    log("SAMPLE PROMPT PER CONDITION (first pair, first wording assignment)")
    log("-" * 92)
    for key, name, h, w, rb, cues, var, _, _ in CONDITIONS:
        log(f"\n### {key} — {name}  [{cues} cue(s), {var}]")
        log(sample_prompt(h, w, pairs[0]))

    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32)
    model.eval()

    log("\n" + "-" * 92)
    log("EVALUATING")
    log("-" * 92)
    all_effects, all_cells, passes = {}, {}, 0
    for key, name, h, w, rb, cues, var, rlabel, note in CONDITIONS:
        eff, cells, np_ = evaluate_condition(model, tok, pairs, h, w, rb, key, log)
        all_effects[key], all_cells[key] = eff, cells
        passes += np_
    log(f"\nTotal forward passes executed: {passes}")

    # ------------------------------------------------- GLOBAL keep set (AC2 policy)
    flagged = set()
    per_cond_flags = {}
    for key in all_effects:
        bad = flag_outliers(all_effects[key])
        per_cond_flags[key] = [pairs[i][0] + "/" + pairs[i][1] for i in bad]
        flagged.update(bad)
    keep = [i for i in range(len(pairs)) if i not in flagged]

    log("")
    log("=" * 92)
    log("=== GLOBAL OUTLIER POLICY (one keep set for every aggregate and contrast)")
    log("=" * 92)
    for key in all_effects:
        log(f"  {key:<6} flagged: {per_cond_flags[key] if per_cond_flags[key] else 'none'}")
    log(f"\n  Dropped globally ({len(flagged)}): "
        f"{sorted(pairs[i][0] + '/' + pairs[i][1] for i in flagged)}")
    log(f"  GLOBAL keep set  (n={len(keep)}): "
        f"{[pairs[i][0] + '/' + pairs[i][1] for i in keep]}")
    if len(keep) < 4:
        raise SystemExit("Global keep set too small for BCa; inspect the flags above.")

    for key, name, h, w, rb, cues, var, rlabel, note in CONDITIONS:
        report(key, name, all_effects[key], all_cells[key], pairs, keep, log,
               rlabel, cues, note)

    store = {}
    run_contrasts(slice_S(all_effects, keep), log, store,
                  f"PRIMARY — global keep set, n={len(keep)}")

    store_sens = {}
    run_contrasts(slice_S(all_effects, list(range(len(pairs)))), log, store_sens,
                  f"SENSITIVITY — all pairs, NO outlier filtering, n={len(pairs)}")

    log("")
    log("=" * 92)
    log("=== PRIMARY vs SENSITIVITY: any contrast whose CI changes zero-coverage")
    log("=" * 92)
    flips = []
    for k in store:
        if k not in store_sens:
            continue
        p, s = store[k], store_sens[k]
        pz = p["ci_lo"] <= 0 <= p["ci_hi"]
        sz = s["ci_lo"] <= 0 <= s["ci_hi"]
        if pz != sz or np.sign(p["mean"]) != np.sign(s["mean"]):
            flips.append(k)
            log(f"  UNSTABLE: {k}")
            log(f"     primary  {p['mean']:+7.3f} [{p['ci_lo']:+.3f}, {p['ci_hi']:+.3f}]")
            log(f"     all-pairs{s['mean']:+7.3f} [{s['ci_lo']:+.3f}, {s['ci_hi']:+.3f}]")
    if not flips:
        log("  None. Every contrast keeps its sign and zero-coverage under both policies.")
    else:
        log(f"\n  {len(flips)} contrast(s) are outlier-policy dependent. Do not headline "
            f"them without stating the policy.")

    payload = {
        "meta": {
            "series": "AD",
            "timestamp": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "model": MODEL_ID, "dtype": "float32", "seed": SEED,
            "n_resamples": N_RESAMPLES, "tost_bound": TOST_BOUND,
            "outlier_token": OUTLIER_TOKEN, "outlier_order": OUTLIER_ORDER,
            "forward_passes": passes,
            "python": sys.version.split()[0], "torch": torch.__version__,
            "transformers": transformers.__version__, "numpy": np.__version__,
            "scipy": scipy.__version__, "platform": platform.platform(),
        },
        "pairs_all": [f"{a}/{b}" for a, b, _, _ in pairs],
        "pairs_kept": [f"{pairs[i][0]}/{pairs[i][1]}" for i in keep],
        "pairs_dropped": sorted(f"{pairs[i][0]}/{pairs[i][1]}" for i in flagged),
        "per_condition_flags": per_cond_flags,
        "conditions": {
            key: {"name": name, "cues": cues, "variation": var, "role_bound": rb,
                  "headers": list(h), "wordings": [list(x) for x in w],
                  "effects_all_items": all_effects[key].tolist(),
                  "raw_cells_all_items": all_cells[key].tolist()}
            for key, name, h, w, rb, cues, var, _, _ in CONDITIONS
        },
        "contrasts_primary": store,
        "contrasts_sensitivity": store_sens,
        "unstable_contrasts": flips,
    }
    with open(args.json, "w") as f:
        json.dump(payload, f, indent=2)
    log(f"\n[json written to {args.json}]")
    log.save(args.out)


if __name__ == "__main__":
    main()
