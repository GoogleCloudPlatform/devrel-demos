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
run_z_series.py — Project Lantern Z-Series
2x2 factorial: {neutral, authority} headers x {verbatim, paraphrased} body.
Fixes the Z-draft's role/wording aliasing by counterbalancing wording assignment.
Outputs: raw cells, per-item table, BCa CIs, outlier flags, factorial contrasts, TOST.
"""
import json, math, argparse
import numpy as np
import torch
from scipy import stats
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "google/gemma-4-e4b"
QUESTION = "Question: What template should I use for project planning?\nAnswer:"

# Two role-neutral surface forms of the SAME proposition.
W1 = "The recommended template for project planning is {e}."
W2 = "For project planning, the template we use is {e}."

H_NEUTRAL   = ("Memo Kestrel", "Memo Larkin")             # (stale-role, recent-role)
H_AUTHORITY = ("OFFICIAL GUIDELINE (2019)", "Team Update (Yesterday)")

CANDIDATES = [
    (" Scrum", " Kanban"), (" Agile", " Waterfall"), (" Roadmap", " Milestone"),
    (" Spec", " Brief"), (" Scope", " Scale"), (" Phase", " Stage"),
    (" Cycle", " Sprint"), (" Board", " Grid"), (" Matrix", " Table"),
    (" Guide", " Manual"), (" Index", " Log"), (" Deck", " Pitch"),
    (" Queue", " Roster"), (" Plan", " Draft"), (" Chart", " Graph"),
]

OUTLIER_TOKEN = 2.0   # |Token| above this => tokenization / base-rate pathology
OUTLIER_ORDER = 0.50  # |Block-Order| above this => item-level null-control failure


# ----------------------------------------------------------------------------- setup
def build_valid_pairs(tok, n_target=10):
    out = []
    for a, b in CANDIDATES:
        ia, ib = tok.encode(a, add_special_tokens=False), tok.encode(b, add_special_tokens=False)
        if len(ia) == 1 and len(ib) == 1:            # <-- MANDATORY single-token filter (Y1)
            out.append((a.strip(), b.strip(), ia[0], ib[0]))
            if len(out) == n_target:
                break
    return out


def build_prompt(h_first, body_first, ent_first, h_second, body_second, ent_second):
    return (f"Context:\n[{h_first}]\n{body_first.format(e=ent_first)}\n\n"
            f"[{h_second}]\n{body_second.format(e=ent_second)}\n\n{QUESTION}")


def log_diff(model, tok, prompt, id_a, id_b):
    """Returns log P(B) - log P(A) at the final position. Same orientation for all cells."""
    inputs = tok(prompt, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits[0, -1, :].float()
    logp = torch.log_softmax(logits, dim=-1)
    return (logp[id_b] - logp[id_a]).item()


# ------------------------------------------------------------------------ evaluation
def evaluate_condition(model, tok, pairs, headers, paraphrased):
    """
    headers = (header_stale_role, header_recent_role)
    paraphrased: False -> both blocks use W1 (verbatim, degenerate)
                 True  -> blocks use {W1,W2}, counterbalanced over which block gets which
    Returns effects (n,4) and mean raw cells (n,4).
    """
    h_stale, h_recent = headers
    wordings = [(W1, W2), (W2, W1)] if paraphrased else [(W1, W1)]

    effects, cells = [], []
    for A, B, idA, idB in pairs:
        acc = np.zeros(4)
        for bf, bs in wordings:
            # Q1: stale-role block FIRST,  entities (stale=A, recent=B)
            e1 = log_diff(model, tok, build_prompt(h_stale, bf, A, h_recent, bs, B), idA, idB)
            # Q2: recent-role block FIRST, entities (stale=A, recent=B)
            e2 = log_diff(model, tok, build_prompt(h_recent, bf, B, h_stale, bs, A), idA, idB)
            # Q3: stale-role block FIRST,  entities SWAPPED (stale=B, recent=A)
            e3 = log_diff(model, tok, build_prompt(h_stale, bf, B, h_recent, bs, A), idA, idB)
            # Q4: recent-role block FIRST, entities SWAPPED (stale=B, recent=A)
            e4 = log_diff(model, tok, build_prompt(h_recent, bf, A, h_stale, bs, B), idA, idB)
            acc += np.array([e1, e2, e3, e4])
        e1, e2, e3, e4 = acc / len(wordings)

        token  = (e1 + e2 + e3 + e4) / 4   # base preference for B over A
        role   = (e1 + e2 - e3 - e4) / 4   # effect of occupying the recent/update ROLE
        order  = (e1 - e2 + e3 - e4) / 4   # NULL CONTROL: prompt-order main effect
        serial = (e1 - e2 - e3 + e4) / 4   # + = recency, - = primacy
        effects.append([token, role, order, serial])
        cells.append([e1, e2, e3, e4])
    return np.array(effects), np.array(cells)


# ------------------------------------------------------------------------ statistics
def bca(x, cl=0.95):
    x = np.asarray(x, dtype=float)
    if np.var(x) == 0 or len(x) < 3:
        return float(np.mean(x)), float(np.mean(x))
    r = stats.bootstrap((x,), np.mean, method="bca", confidence_level=cl,
                        n_resamples=9999, random_state=42)
    return float(r.confidence_interval.low), float(r.confidence_interval.high)


def fmt(x, label, cl=0.95):
    lo, hi = bca(x, cl)
    star = "" if (lo <= 0 <= hi) else "  *"
    return f"{label:<34} {np.mean(x):+7.3f}  [{lo:+.3f}, {hi:+.3f}]{star}"


def tost(x, bound):
    """Two one-sided t-tests + 90% BCa CI (the CI is the primary report)."""
    x = np.asarray(x, dtype=float); n = len(x)
    se = np.std(x, ddof=1) / np.sqrt(n)
    p_lo = stats.t.sf((np.mean(x) + bound) / se, df=n - 1)
    p_hi = stats.t.cdf((np.mean(x) - bound) / se, df=n - 1)
    p = max(p_lo, p_hi)
    lo90, hi90 = bca(x, cl=0.90)
    return p, (lo90, hi90), (p < 0.05 and -bound <= lo90 and hi90 <= bound)


def flag_outliers(effects, pairs):
    bad = [i for i in range(len(pairs))
           if abs(effects[i, 0]) > OUTLIER_TOKEN or abs(effects[i, 2]) > OUTLIER_ORDER]
    return bad


# ---------------------------------------------------------------------------- report
def report(name, effects, cells, pairs, bound, out):
    def w(s=""):
        print(s); out.append(s)
    w(f"\n=== {name} ===")
    w("\nRaw cells (e1,e2,e3,e4) and effects:")
    w(f"{'item':<24}{'e1':>8}{'e2':>8}{'e3':>8}{'e4':>8} | {'Tok':>7}{'Role':>8}{'Ord':>8}{'Ser':>8}")
    for i, (A, B, _, _) in enumerate(pairs):
        c, e = cells[i], effects[i]
        w(f"{A+'/'+B:<24}{c[0]:>8.3f}{c[1]:>8.3f}{c[2]:>8.3f}{c[3]:>8.3f} | "
          f"{e[0]:>7.3f}{e[1]:>8.3f}{e[2]:>8.3f}{e[3]:>8.3f}")

    bad = flag_outliers(effects, pairs)
    if bad:
        w(f"\nWARNING: {len(bad)} outliers detected: {[pairs[i][0].strip()+'/'+pairs[i][1].strip() for i in bad]}")
    
    clean_idx = [i for i in range(len(pairs)) if i not in bad]
    if len(clean_idx) < 3:
        w("Too few clean items to compute statistics.")
        return effects, cells, bad

    clean_eff = effects[clean_idx]
    w(f"\nAggregates (n={len(clean_idx)} clean items):")
    w(fmt(clean_eff[:, 0], "Token Effect"))
    w(fmt(clean_eff[:, 1], "Role/Semantic Effect"))
    w(fmt(clean_eff[:, 2], "Block-Order Effect"))
    w(fmt(clean_eff[:, 3], "Serial Position Effect"))
    
    p, ci90, sig = tost(clean_eff[:, 3], bound)
    w(f"TOST test for Serial Position (bound={bound}): Equivalent={sig} (p={p:.4f}, 90% CI: [{ci90[0]:.3f}, {ci90[1]:.3f}])")
    
    return clean_eff, cells, bad


def run_z_series():
    print("Loading tokenizer...")
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    pairs = build_valid_pairs(tok)
    print(f"Found {len(pairs)} valid single-token congruent pairs.")
    
    if len(pairs) < 10:
        print("Need at least 10 valid pairs.")
        return

    print("Loading fp32 model...")
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32)
    model.eval()

    out = []
    
    # 2x2 Factorial Design
    print("\n--- Running T1 (Neutral Headers, Verbatim Body) ---")
    eff_t1, cells_t1 = evaluate_condition(model, tok, pairs, H_NEUTRAL, paraphrased=False)
    
    print("\n--- Running T2 (Neutral Headers, Paraphrased Body) ---")
    eff_t2, cells_t2 = evaluate_condition(model, tok, pairs, H_NEUTRAL, paraphrased=True)
    
    print("\n--- Running T3 (Authority Headers, Verbatim Body) ---")
    eff_t3, cells_t3 = evaluate_condition(model, tok, pairs, H_AUTHORITY, paraphrased=False)
    
    print("\n--- Running T4 (Authority Headers, Paraphrased Body) ---")
    eff_t4, cells_t4 = evaluate_condition(model, tok, pairs, H_AUTHORITY, paraphrased=True)
    
    report("T1: Neutral Headers, Verbatim Body", eff_t1, cells_t1, pairs, bound=0.15, out=out)
    report("T2: Neutral Headers, Paraphrased Body (THE DECISIVE TEST)", eff_t2, cells_t2, pairs, bound=0.15, out=out)
    report("T3: Authority Headers, Verbatim Body", eff_t3, cells_t3, pairs, bound=0.15, out=out)
    report("T4: Authority Headers, Paraphrased Body", eff_t4, cells_t4, pairs, bound=0.15, out=out)

    with open("/path/to/your/project.txt", "w") as f:
        f.write("\n".join(out))

if __name__ == "__main__":
    run_z_series()
