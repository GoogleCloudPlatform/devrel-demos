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
run_ac_series.py — Project Lantern AC-Series (FINAL)
=====================================================
Fixes AC1 (T4c never implemented -> "cue-matched" claim was false),
     AC2 (paired contrasts used n=10 while aggregates used n=9),
     AC3 (magnitude fragility must be reported),
     AC4 (interaction computed from cue-contaminated cells),
     AC6 (no provenance header).

Bodies
------
W1  "The recommended template for project planning is {e}."        CUE PRESENT ("is {e}")
W2  "{e} is the template we use for project planning."             cue-free (sentence-initial)
W3  "{e} remains our standard project planning template."          cue-free (sentence-initial)
Y1  "Official guidelines state ... the required configuration is {e}."   LOADED, cue present
Y2  "Update: The new updated specification ... is now {e}."              LOADED, cue present
Y1b "{e} is the required configuration for Project Planning Template,
     per official guidelines."                                           LOADED, cue-free
Y2b "{e} is the newly updated specification for Project Planning
     Template, effective now."                                          LOADED, cue-free

"Cue" = the entity appearing immediately after "is"/"is now", i.e. the local
n-gram an induction/copy head can key on. W2/W3/Y1b/Y2b place {e} sentence-initially,
so its left-context is "\n", not a repeated trigram.

Conditions (480 forward passes, one fp32 load)
----------------------------------------------
T1   Neutral   x (W1,W1)                role_bound=False   2 cues   40
T2   Neutral   x (W1,W2),(W2,W1)        role_bound=False   1 cue    80
T2c  Neutral   x (W2,W3),(W3,W2)        role_bound=False   0 cues   80   <- cue-free neutral
T3   Authority x (W1,W1)                role_bound=False   2 cues   40
T4   Authority x (W1,W2),(W2,W1)        role_bound=False   1 cue    80
T4c  Authority x (W2,W3),(W3,W2)        role_bound=False   0 cues   80   <- baseline for T5b
T5   Authority x (Y1,Y2)                role_bound=True    2 cues   40
T5b  Authority x (Y1b,Y2b)              role_bound=True    0 cues   40   <- HEAD-TO-HEAD

Contrast algebra (identical orientation in every cell)
------------------------------------------------------
e_i = log P(B) - log P(A) at the final position.
  Q1 stale-role block FIRST,  stale=A recent=B
  Q2 recent-role block FIRST, stale=A recent=B
  Q3 stale-role block FIRST,  stale=B recent=A
  Q4 recent-role block FIRST, stale=B recent=A

  Token  = (e1+e2+e3+e4)/4   base preference for B over A
  Role   = (e1+e2-e3-e4)/4   recent-role effect (T5/T5b: source-framing, aliased w/ body)
  Order  = (e1-e2+e3-e4)/4   NULL CONTROL
  Serial = (e1-e2-e3+e4)/4   + recency / - primacy    [HALF-EFFECT; full swing = 2 x Serial]

Outlier policy (AC2)
--------------------
Per-condition flags: |Token| > 2.0 (tokenization/base-rate pathology)
                     |Order| > 0.50 (item-level null-control failure)
GLOBAL KEEP SET = intersection of unflagged items across ALL conditions.
Every aggregate and every paired contrast uses that identical index set.
Per-condition flags are still printed for diagnosis.
"""

import argparse
import datetime
import json
import platform
import sys

import numpy as np
import scipy
import torch
from scipy import stats
from transformers import AutoTokenizer, AutoModelForCausalLM
import transformers

# ------------------------------------------------------------------ configuration
MODEL_ID = "google/gemma-4-e4b"
SEED = 42
N_RESAMPLES = 9999
TOST_BOUND = 0.15
OUTLIER_TOKEN = 2.0
OUTLIER_ORDER = 0.50

DEFAULT_TXT = "o2_results_ac_series.txt"
DEFAULT_JSON = "o2_results_ac_series.json"

QUESTION = "Question: What template should I use for project planning?\nAnswer:"

# --- Role-NEUTRAL bodies --------------------------------------------------------
W1 = "The recommended template for project planning is {e}."          # cue present
W2 = "{e} is the template we use for project planning."               # cue-free
W3 = "{e} remains our standard project planning template."            # cue-free

# --- Role-LOADED bodies (body IS the manipulation) ------------------------------
Y1 = ("Official guidelines state that for Project Planning Template, "
      "the required configuration is {e}.")                            # cue present
Y2 = ("Update: The new updated specification for Project Planning Template "
      "is now {e}.")                                                   # cue present

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
def build_valid_pairs(tok, n_target=10):
    """MANDATORY single-token filter (Y1 regression guard)."""
    kept, rejected = [], []
    for a, b in CANDIDATES:
        ia = tok.encode(a, add_special_tokens=False)
        ib = tok.encode(b, add_special_tokens=False)
        if len(ia) == 1 and len(ib) == 1:
            if len(kept) < n_target:
                kept.append((a.strip(), b.strip(), ia[0], ib[0]))
        else:
            rejected.append((a.strip(), b.strip(), len(ia), len(ib)))
    return kept, rejected


def build_prompt(h1, body1, e1, h2, body2, e2):
    return (f"Context:\n[{h1}]\n{body1.format(e=e1)}\n\n"
            f"[{h2}]\n{body2.format(e=e2)}\n\n{QUESTION}")


def log_diff(model, tok, prompt, id_a, id_b):
    inputs = tok(prompt, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits[0, -1, :].float()
    logp = torch.log_softmax(logits, dim=-1)
    return (logp[id_b] - logp[id_a]).item()


# --------------------------------------------------------------------- evaluation
def evaluate_condition(model, tok, pairs, headers, wordings, role_bound, key, log):
    """
    role_bound=False -> (body_for_FIRST_block, body_for_SECOND_block); pass BOTH
                        orders so surface form is orthogonal to role AND to position.
    role_bound=True  -> (body_for_STALE_role, body_for_RECENT_role); EXACTLY ONE
                        assignment. Counterbalancing here averages the semantic
                        manipulation to zero (the AB1 bug). Enforced below.
    """
    if role_bound and len(wordings) != 1:
        raise ValueError(
            f"[{key}] role_bound=True requires exactly one wording assignment; got "
            f"{len(wordings)}. Counterbalancing cancels the manipulation (AB1)."
        )
    if not role_bound and len(wordings) == 2:
        (a1, b1), (a2, b2) = wordings
        if not (a1 == b2 and b1 == a2):
            raise ValueError(f"[{key}] role_bound=False pair is not a proper "
                             f"counterbalance of the same two bodies.")

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


def count_cues(wordings, role_bound):
    """Number of 'is {e}' local copy cues per prompt (bodies containing 'is {e}')."""
    bx, by = wordings[0]
    return sum(1 for b in (bx, by) if "is {e}" in b or "is now {e}" in b)


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


# ------------------------------------------------------------------------- report
def report(key, name, effects, cells, pairs, keep, log, role_label, note=None):
    """`keep` is the GLOBAL index set. Aggregates use it verbatim (AC2)."""
    log("")
    log("=" * 88)
    log(f"=== {key}: {name}")
    log("=" * 88)
    if note:
        log(f"NOTE: {note}")

    log("")
    log("Per-item raw cells (e1..e4) and derived effects   [AB4/AC2 dump; "
        "'X' = dropped by global policy]:")
    log(f"{'':2}{'item':<20}{'e1':>9}{'e2':>9}{'e3':>9}{'e4':>9} | "
        f"{'Token':>8}{'Role':>9}{'Order':>8}{'Serial':>9}")
    log("-" * 88)
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
    log(f"  -> Order null {'PASSES' if olo <= 0 <= ohi else 'FAILS'} "
        f"(CI {'covers' if olo <= 0 <= ohi else 'excludes'} zero).")
    if "Source-Framing" not in role_label:
        rlo, rhi = bca(clean[:, 1])
        log(f"  -> Role null {'PASSES' if rlo <= 0 <= rhi else 'FAILS'}.")

    ser = clean[:, 3]
    log(f"  -> Full first-vs-last swing = {2 * np.mean(ser):+.3f} nats.")
    log(f"  -> Sign consistency: {int(np.sum(ser < 0))}/{len(ser)} items negative (primacy).")
    p, ci90, eq = tost(ser)
    log(f"  -> TOST vs +/-{TOST_BOUND}: equivalent={eq} (p={p:.4f}, 90% CI "
        f"[{ci90[0]:+.3f}, {ci90[1]:+.3f}]). Non-rejection != equality.")
    return clean[:, 3]


def paired(a, b, label, log, store, cl=0.95):
    """Paired per-item contrast a-b. Both vectors are already on the global keep set."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    assert a.shape == b.shape, f"{label}: shape mismatch {a.shape} vs {b.shape}"
    d = a - b
    lo, hi = bca(d, cl)
    flag = "" if (lo <= 0 <= hi) else "  *"
    log(f"{label:<50} {np.mean(d):+7.3f}  [{lo:+.3f}, {hi:+.3f}]{flag}   "
        f"(SD={np.std(d, ddof=1):.3f}, n={len(d)})")
    store[label] = {"mean": float(np.mean(d)), "ci_lo": lo, "ci_hi": hi,
                    "sd": float(np.std(d, ddof=1)), "n": int(len(d))}
    return d


# ---------------------------------------------------------------------------- run
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_TXT)
    ap.add_argument("--json", default=DEFAULT_JSON)
    ap.add_argument("--n-pairs", type=int, default=10)
    args = ap.parse_args()

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.use_deterministic_algorithms(False)

    log = Log()

    # ---------------------------------------------------------- provenance (AC6)
    log("=" * 88)
    log("PROJECT LANTERN — AC-SERIES  (final, cue-matched)")
    log("=" * 88)
    log(f"timestamp     : {datetime.datetime.now().astimezone().isoformat(timespec='seconds')}")
    log(f"model         : {MODEL_ID}    dtype=float32    eval mode, no sampling")
    log(f"seed          : {SEED}        BCa resamples: {N_RESAMPLES}")
    log(f"python        : {sys.version.split()[0]}")
    log(f"torch         : {torch.__version__}   transformers: {transformers.__version__}")
    log(f"numpy         : {np.__version__}      scipy: {scipy.__version__}")
    log(f"platform      : {platform.platform()}")
    log(f"outlier rule  : |Token|>{OUTLIER_TOKEN} or |Order|>{OUTLIER_ORDER}; "
        f"GLOBAL keep set = intersection across all conditions")

    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model.eval()

    pairs, rejected = build_valid_pairs(tok, n_target=args.n_pairs)
    log(f"Valid pairs ({len(pairs)}): {[p[0] + '/' + p[1] for p in pairs]}")
    log(f"Rejected pairs ({len(rejected)}): {[(a, b, la, lb) for a, b, la, lb in rejected]}")

    log("\nSample Prompt (T5b):\n")
    log(sample_prompt(H_AUTHORITY, [(Y1b, Y2b)], pairs[0]))

    # --- Run Evaluations ---
    store = {}
    
    # T1: Neutral Headers, Verbatim Body
    eff_t1, cells_t1, _ = evaluate_condition(model, tok, pairs, H_NEUTRAL, [(W1, W1)], role_bound=False, key="T1", log=log)
    # T2: Neutral Headers, Paraphrased Body (W1/W2 counterbalanced)
    eff_t2, cells_t2, _ = evaluate_condition(model, tok, pairs, H_NEUTRAL, [(W1, W2), (W2, W1)], role_bound=False, key="T2", log=log)
    # T2c: Neutral Headers, Cue-Free Body (W2/W3 counterbalanced)
    eff_t2c, cells_t2c, _ = evaluate_condition(model, tok, pairs, H_NEUTRAL, [(W2, W3), (W3, W2)], role_bound=False, key="T2c", log=log)
    # T3: Authority Headers, Verbatim Body
    eff_t3, cells_t3, _ = evaluate_condition(model, tok, pairs, H_AUTHORITY, [(W1, W1)], role_bound=False, key="T3", log=log)
    # T4: Authority Headers, Paraphrased Body (W1/W2)
    eff_t4, cells_t4, _ = evaluate_condition(model, tok, pairs, H_AUTHORITY, [(W1, W2), (W2, W1)], role_bound=False, key="T4", log=log)
    # T4c: Authority Headers, Cue-Free Body (W2/W3)
    eff_t4c, cells_t4c, _ = evaluate_condition(model, tok, pairs, H_AUTHORITY, [(W2, W3), (W3, W2)], role_bound=False, key="T4c", log=log)
    # T5: Authority Headers, Loaded Bodies (No counterbalancing)
    eff_t5, cells_t5, _ = evaluate_condition(model, tok, pairs, H_AUTHORITY, [(Y1, Y2)], role_bound=True, key="T5", log=log)
    # T5b: Authority Headers, Cue-Matched Loaded Bodies
    eff_t5b, cells_t5b, _ = evaluate_condition(model, tok, pairs, H_AUTHORITY, [(Y1b, Y2b)], role_bound=True, key="T5b", log=log)

    # --- Outlier Policy ---
    all_effects = [eff_t1, eff_t2, eff_t2c, eff_t3, eff_t4, eff_t4c, eff_t5, eff_t5b]
    global_bad = set()
    for eff in all_effects:
        global_bad.update(flag_outliers(eff))
    keep = [i for i in range(len(pairs)) if i not in global_bad]
    
    log(f"\nGLOBAL KEEP SET: {len(keep)} items.")
    if global_bad:
        log(f"Dropped {len(global_bad)} items globally: {[pairs[i][0] + '/' + pairs[i][1] for i in global_bad]}")

    # --- Reports ---
    s_t1 = report("T1", "Neutral Headers, Verbatim Body", eff_t1, cells_t1, pairs, keep, log, "Role-Framing Effect")
    s_t2 = report("T2", "Neutral Headers, Paraphrased Body (W1/W2)", eff_t2, cells_t2, pairs, keep, log, "Role-Framing Effect")
    s_t2c = report("T2c", "Neutral Headers, Cue-Free Body (W2/W3)", eff_t2c, cells_t2c, pairs, keep, log, "Role-Framing Effect")
    s_t3 = report("T3", "Authority Headers, Verbatim Body", eff_t3, cells_t3, pairs, keep, log, "Role-Framing Effect")
    s_t4 = report("T4", "Authority Headers, Paraphrased Body (W1/W2)", eff_t4, cells_t4, pairs, keep, log, "Role-Framing Effect")
    s_t4c = report("T4c", "Authority Headers, Cue-Free Body (W2/W3)", eff_t4c, cells_t4c, pairs, keep, log, "Role-Framing Effect")
    s_t5 = report("T5", "Authority Headers, Loaded Bodies (Y1/Y2)", eff_t5, cells_t5, pairs, keep, log, "Source-Framing (header+body)")
    s_t5b = report("T5b", "Authority Headers, Cue-Matched Loaded Bodies", eff_t5b, cells_t5b, pairs, keep, log, "Source-Framing (header+body)")

    log("\n")
    log("=" * 88)
    log("=== Pre-registered Contrasts (on global keep set)")
    log("=" * 88)

    paired(s_t5b, s_t4c, "T5b - T4c (Semantic Suppression | Cue-Matched)", log, store)
    
    interact = (s_t4c - s_t2c) - (s_t3 - s_t1)
    paired(interact, np.zeros_like(interact), "Cue-free Interaction (Header * Body Paraphrase)", log, store)
    
    paired(s_t4c, s_t2c, "T4c - T2c (Authority vs Neutral | Cue-Free)", log, store)
    paired(s_t2, s_t1, "T2 - T1 (Induction vs True Primacy)", log, store)
    paired(s_t2c, s_t2, "T2c - T2 (Removing last cue vs 1 cue)", log, store)

    log.save(args.out)
    with open(args.json, "w") as f:
        json.dump(store, f, indent=2)

if __name__ == "__main__":
    main()
