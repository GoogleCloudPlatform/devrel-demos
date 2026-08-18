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
run_aa_series.py — Project Lantern AA-Series
"""
import math
import numpy as np
import torch
from scipy import stats
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "google/gemma-4-e4b"
QUESTION = "Question: What template should I use for project planning?\nAnswer:"

# Two role-neutral surface forms of the SAME proposition, with differing left-context
W1 = "The recommended template for project planning is {e}."
W2 = "{e} is the template we use for project planning."

# Y-series semantically loaded bodies
Y1 = "Official guidelines state that for Project Planning Template, the required configuration is {e}."
Y2 = "Update: The new updated specification for Project Planning Template is now {e}."

H_NEUTRAL   = ("Memo Kestrel", "Memo Larkin")             # (stale-role, recent-role)
H_AUTHORITY = ("OFFICIAL GUIDELINE (2019)", "Team Update (Yesterday)")

CANDIDATES = [
    (" Scrum", " Kanban"), (" Agile", " Waterfall"), (" Roadmap", " Milestone"),
    (" Spec", " Brief"), (" Scope", " Scale"), (" Phase", " Stage"),
    (" Cycle", " Sprint"), (" Board", " Grid"), (" Matrix", " Table"),
    (" Guide", " Manual"), (" Index", " Log"), (" Deck", " Pitch"),
    (" Queue", " Roster"), (" Plan", " Draft"), (" Chart", " Graph"),
]

OUTLIER_TOKEN = 2.0
OUTLIER_ORDER = 0.50

def build_valid_pairs(tok, n_target=10):
    out = []
    for a, b in CANDIDATES:
        ia, ib = tok.encode(a, add_special_tokens=False), tok.encode(b, add_special_tokens=False)
        if len(ia) == 1 and len(ib) == 1:
            out.append((a.strip(), b.strip(), ia[0], ib[0]))
            if len(out) == n_target:
                break
    return out

def build_prompt(h_first, body_first, ent_first, h_second, body_second, ent_second):
    return (f"Context:\n[{h_first}]\n{body_first.format(e=ent_first)}\n\n"
            f"[{h_second}]\n{body_second.format(e=ent_second)}\n\n{QUESTION}")

def log_diff(model, tok, prompt, id_a, id_b):
    inputs = tok(prompt, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits[0, -1, :].float()
    logp = torch.log_softmax(logits, dim=-1)
    return (logp[id_b] - logp[id_a]).item()

def evaluate_condition(model, tok, pairs, headers, wordings, role_bound):
    h_stale, h_recent = headers
    effects, cells = [], []
    for A, B, idA, idB in pairs:
        acc = np.zeros(4)
        for bx, by in wordings:
            if role_bound:
                b_stale, b_recent = bx, by
                f1, s1 = b_stale, b_recent
                f2, s2 = b_recent, b_stale
            else:
                f1, s1 = bx, by
                f2, s2 = bx, by

            e1 = log_diff(model, tok, build_prompt(h_stale, f1, A, h_recent, s1, B), idA, idB)
            e2 = log_diff(model, tok, build_prompt(h_recent, f2, B, h_stale, s2, A), idA, idB)
            e3 = log_diff(model, tok, build_prompt(h_stale, f1, B, h_recent, s1, A), idA, idB)
            e4 = log_diff(model, tok, build_prompt(h_recent, f2, A, h_stale, s2, B), idA, idB)
            acc += np.array([e1, e2, e3, e4])

        c1, c2, c3, c4 = acc / len(wordings)
        token = (c1 + c2 + c3 + c4) / 4
        role  = (c1 + c2 - c3 - c4) / 4
        order = (c1 - c2 + c3 - c4) / 4
        serial = (c1 - c2 - c3 + c4) / 4
        effects.append([token, role, order, serial])
        cells.append([c1, c2, c3, c4])
    return np.array(effects), np.array(cells)

def bca(x, cl=0.95):
    x = np.asarray(x, dtype=float)
    if np.var(x) == 0 or len(x) < 3:
        return float(np.mean(x)), float(np.mean(x))
    r = stats.bootstrap((x,), np.mean, method="bca", confidence_level=cl, n_resamples=9999, random_state=42)
    return float(r.confidence_interval.low), float(r.confidence_interval.high)

def fmt(x, label, cl=0.95):
    lo, hi = bca(x, cl)
    star = "" if (lo <= 0 <= hi) else "  *"
    return f"{label:<34} {np.mean(x):+7.3f}  [{lo:+.3f}, {hi:+.3f}]{star}"

def tost(x, bound):
    x = np.asarray(x, dtype=float); n = len(x)
    se = np.std(x, ddof=1) / np.sqrt(n)
    p_lo = stats.t.sf((np.mean(x) + bound) / se, df=n - 1)
    p_hi = stats.t.cdf((np.mean(x) - bound) / se, df=n - 1)
    p = max(p_lo, p_hi)
    lo90, hi90 = bca(x, cl=0.90)
    return p, (lo90, hi90), (p < 0.05 and -bound <= lo90 and hi90 <= bound)

def report(name, effects, cells, pairs, out):
    def w(s=""):
        print(s); out.append(s)
    w(f"\n=== {name} ===")
    bad = [i for i in range(len(pairs)) if abs(effects[i, 0]) > OUTLIER_TOKEN or abs(effects[i, 2]) > OUTLIER_ORDER]
    clean_idx = [i for i in range(len(pairs)) if i not in bad]
    
    clean_eff = effects[clean_idx]
    w(f"Aggregates (n={len(clean_idx)} clean items):")
    w(fmt(clean_eff[:, 0], "Token Effect"))
    w(fmt(clean_eff[:, 1], "Role Effect"))
    w(fmt(clean_eff[:, 2], "Block-Order Effect"))
    w(fmt(clean_eff[:, 3], "Serial Position Effect"))
    p, ci90, sig = tost(clean_eff[:, 3], 0.15)
    w(f"TOST test for Serial Position (bound=0.15): Equivalent={sig} (p={p:.4f}, 90% CI: [{ci90[0]:.3f}, {ci90[1]:.3f}])")
    return clean_eff[:, 3]

def run_aa_series():
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    pairs = build_valid_pairs(tok)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32)
    model.eval()

    out = []
    
    # T1: Neutral Headers, Verbatim Body
    eff_t1, cells_t1 = evaluate_condition(model, tok, pairs, H_NEUTRAL, [(W1, W1)], role_bound=False)
    # T2: Neutral Headers, Paraphrased Body
    eff_t2, cells_t2 = evaluate_condition(model, tok, pairs, H_NEUTRAL, [(W1, W2), (W2, W1)], role_bound=False)
    # T3: Authority Headers, Verbatim Body
    eff_t3, cells_t3 = evaluate_condition(model, tok, pairs, H_AUTHORITY, [(W1, W1)], role_bound=False)
    # T4: Authority Headers, Paraphrased Body
    eff_t4, cells_t4 = evaluate_condition(model, tok, pairs, H_AUTHORITY, [(W1, W2), (W2, W1)], role_bound=False)
    # T5: Authority Headers, Loaded Bodies (Counterbalanced)
    eff_t5, cells_t5 = evaluate_condition(model, tok, pairs, H_AUTHORITY, [(Y1, Y2), (Y2, Y1)], role_bound=True)
    
    s_t1 = report("T1: Neutral Headers, Verbatim Body", eff_t1, cells_t1, pairs, out)
    s_t2 = report("T2: Neutral Headers, Paraphrased Body (Initial-Entity)", eff_t2, cells_t2, pairs, out)
    s_t3 = report("T3: Authority Headers, Verbatim Body", eff_t3, cells_t3, pairs, out)
    s_t4 = report("T4: Authority Headers, Paraphrased Body", eff_t4, cells_t4, pairs, out)
    s_t5 = report("T5: Authority Headers, Loaded Bodies (Matched)", eff_t5, cells_t5, pairs, out)

    def paired_diff(a, b, label):
        d = a - b
        lo, hi = bca(d)
        flag = "*" if not (lo <= 0 <= hi) else ""
        s = f"{label:<40} {np.mean(d):+7.3f}  [{lo:+.3f}, {hi:+.3f}] {flag}"
        print(s); out.append(s)

    out.append("\n=== Factorial & Paired Contrasts ===")
    print("\n=== Factorial & Paired Contrasts ===")
    
    paired_diff(s_t2, s_t1, "T2 - T1 (Induction vs True Primacy)")
    
    h_main = (s_t3 + s_t4)/2 - (s_t1 + s_t2)/2
    paired_diff(h_main, np.zeros_like(h_main), "Header Main Effect on Serial")
    
    b_main = (s_t2 + s_t4)/2 - (s_t1 + s_t3)/2
    paired_diff(b_main, np.zeros_like(b_main), "Body Main Effect on Serial")
    
    paired_diff(s_t5, s_t4, "T5 - T4 (Semantic Suppression)")

    import os
    out_path = os.environ.get("OUTPUT_TXT", "o2_results_aa_series.txt")
    with open(out_path, "w") as f:
        f.write("\n".join(out))

if __name__ == "__main__":
    run_aa_series()
