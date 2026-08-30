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
Negative delta => that (layer, position) carries the recency signal.

No layer window is assumed. The sweep is what determines it.
"""
import json, argparse, torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from j_lens_gemma import GemmaJLens, GEMMA_MODEL_CONFIGS

EXPECTED_SIGN = {"recency": -1, "date_recency": -1, "authority": +1}

FLIP_CANDIDATES = {
    # donor makes the stale block NEWER -> diff should FALL
    "date_recency": {
        "(2019)": ["(2025)", "(2024)", "(2026)"],
        "(2020)": ["(2025)", "(2024)", "(2026)"],
    },
    # donor STRIPS authority from the stale block -> diff should RISE
    "authority": {
        "OFFICIAL GUIDELINE": ["LOCAL RUMOR", "DRAFT PROPOSAL", "UNKNOWN RUMOR", "UNVERIFIED CLAIM"],
        "ENTERPRISE ARCHITECTURE SPECIFICATION": ["UNOFFICIAL DRAFT SPECULATION", "OBSOLETE DRAFT SPECULATION", "REJECTED DRAFT SPECULATION"],
    },
    # donor makes the recent block STALE -> diff should FALL
    "recency": {
        "(Yesterday)": ["(Past)", "(Before)", "(Older)"],
        "(2 hours ago)": ["(2 years ago)", "(9 years ago)", "(2 decades ago)"],
    },
}

def build_donor(prompt, tok, mode):
    n = len(tok(prompt).input_ids)
    for marker, cands in FLIP_CANDIDATES[mode].items():
        if marker not in prompt:
            continue
        for cand in cands:
            cp = prompt.replace(marker, cand, 1)
            if len(tok(cp).input_ids) == n:
                return cp, marker, cand
        raise ValueError(f"F4b: no length-matched flip for '{marker}' "
                         f"(prompt={n} tok). Add candidates to FLIP_CANDIDATES.")
    raise ValueError("F4b: no known recency marker found in prompt.")


def select_positions(prompt, tok, markers, entities, keep_last=6, keep_bos=True):
    enc = tok(prompt, return_offsets_mapping=True, add_special_tokens=True)
    offs = enc["offset_mapping"]
    n = len(enc["input_ids"])
    spans = []
    for s in list(markers) + list(entities):
        if not s:
            continue
        i = prompt.find(s)
        while i != -1:
            spans.append((i, i + len(s)))
            i = prompt.find(s, i + 1)
    keep = set()
    for ti, (a, b) in enumerate(offs):
        if b <= a:                       # special / empty-offset token
            continue
        if any(a < e and b > st for st, e in spans):
            keep.add(ti)
    keep.update(range(max(0, n - keep_last), n))
    if keep_bos:
        keep.add(0)
    return sorted(keep)


@torch.no_grad()
def score(model, tok, prompt, cont, device):
    c = cont if cont.startswith(" ") else " " + cont
    p = tok(prompt, return_tensors="pt").input_ids.to(device)
    k = tok(c, add_special_tokens=False, return_tensors="pt").input_ids.to(device)
    full = torch.cat([p, k], 1)
    
    # slice logits BEFORE log_softmax for massive speedup
    logits = model(full).logits[:, p.shape[1] - 1 : full.shape[1] - 1, :].float()
    lp = torch.log_softmax(logits, -1)
    
    target_ids = k.unsqueeze(-1)
    t = lp.gather(-1, target_ids).squeeze(-1)
    return t.sum().item(), full, p.shape[1]


@torch.no_grad()
def patched_scores(model, mod, donor_act, full_ids, prompt_len, positions, chunk):
    out = []
    for i in range(0, len(positions), chunk):
        blk = positions[i:i + chunk]
        batch = full_ids.repeat(len(blk), 1)
        idx = torch.tensor(blk, device=full_ids.device)

        def hook(m, inp, output, idx=idx):
            t = output[0] if isinstance(output, tuple) else output
            p = t.clone()
            rows = torch.arange(p.shape[0], device=p.device)
            p[rows, idx, :] = donor_act[0, idx, :].to(p.dtype)
            if isinstance(output, tuple):
                r = list(output); r[0] = p; return tuple(r)
            return p

        h = mod.register_forward_hook(hook)
        logits = model(batch).logits[:, prompt_len - 1 : batch.shape[1] - 1, :]
        h.remove()
        lp = torch.log_softmax(logits.float(), -1)
        target_ids = batch[:, prompt_len:].unsqueeze(-1)
        tok_lp = lp.gather(-1, target_ids).squeeze(-1)
        out.extend(tok_lp.sum(-1).tolist())
    return out


def sweep(model, tok, jl, recipient, donor, stale_t, recent_t,
          device, chunk, mode, positions=None):
    r_ids = tok(recipient, return_tensors="pt").to(device)
    d_ids = tok(donor, return_tensors="pt").to(device)
    if r_ids.input_ids.shape[1] != d_ids.input_ids.shape[1]:
        raise ValueError("F4b: donor/recipient token-length mismatch.")

    s_first = tok(" " + stale_t.strip(), add_special_tokens=False).input_ids[0]
    r_first = tok(" " + recent_t.strip(), add_special_tokens=False).input_ids[0]
    if s_first == r_first:
        raise ValueError(f"F2: targets share first token id {s_first} "
                         f"({stale_t!r} vs {recent_t!r}). Baseline item leaked in.")

    # ---- unpatched recipient baseline
    s_base, s_full, plen = score(model, tok, recipient, stale_t, device)
    r_base, r_full, _ = score(model, tok, recipient, recent_t, device)
    base_diff = r_base - s_base

    # ---- unpatched DONOR baseline -> measured ceiling (the 4-forward diagnostic,
    #      now computed inline every run so it can never drift from the heatmap)
    ds_base, _, _ = score(model, tok, donor, stale_t, device)
    dr_base, _, _ = score(model, tok, donor, recent_t, device)
    donor_diff = dr_base - ds_base
    ceiling = donor_diff - base_diff          # SAME sign convention as the heatmap
    exp = EXPECTED_SIGN[mode]

    print(f"    base_diff ={base_diff:+.4f}  donor_diff={donor_diff:+.4f}")
    print(f"    ceiling   ={ceiling:+.4f}  (expected sign {exp:+d})")
    if ceiling * exp <= 0:
        print(f"    [!] F5: ceiling sign contradicts '{mode}' mode. "
              f"The flip is not doing what it claims. DO NOT interpret this heatmap.")
        return {"error": "F5"}
    if abs(ceiling) < 0.05:
        print(f"    [!] F6: |ceiling| < 0.05 nats. Heatmap will be noise-dominated.")
        return {"error": "F6"}

    # ---- donor activations
    jl.register_hooks()
    model(**d_ids)
    donor_acts = {l: a.detach().clone() for l, a in jl.activations.items()}
    jl.remove_hooks()

    if positions is None:
        positions = list(range(plen))
    positions = [p for p in positions if p < plen]

    heat, frac = [], []
    for l in range(jl.num_layers):
        if l not in donor_acts:
            heat.append([0.0] * len(positions))
            frac.append([0.0] * len(positions))
            continue
        mod = jl._get_layer_module(l)
        s_lp = patched_scores(model, mod, donor_acts[l], s_full, plen, positions, chunk)
        r_lp = patched_scores(model, mod, donor_acts[l], r_full, plen, positions, chunk)
        # SIGN CONVENTION (single source of truth):
        #   delta = patched_diff - base_diff
        # A causal site reproduces the donor, so delta -> ceiling.
        row = [(r - s) - base_diff for s, r in zip(s_lp, r_lp)]
        heat.append([round(v, 4) for v in row])
        frac.append([round(v / ceiling, 4) if ceiling else 0.0 for v in row])
        best = max(row, key=abs)
        print(f"  layer {l:>2}  peak={best:+.4f} nats  "
              f"({best/ceiling*100 if ceiling else 0:6.1f}% of ceiling "
              f"{ceiling:+.4f})", flush=True)

    all_tok = tok.convert_ids_to_tokens(r_ids.input_ids[0])
    return {
        "mode": mode,
        "sign_convention": "delta = patched_diff - base_diff; "
                           "causal site -> delta approaches ceiling",
        "expected_sign": exp,
        "num_layers": jl.num_layers,
        "seq_len": plen,
        "base_log_prob_diff": round(base_diff, 4),
        "donor_log_prob_diff": round(donor_diff, 4),
        "ceiling": round(ceiling, 4),
        "ceiling_sign_ok": bool(ceiling * exp > 0),
        "peak_abs_nats": round(max((max(r, key=abs) for r in heat), key=abs), 4) if heat else 0.0,
        "bf16_noise_floor_nats": 0.01,
        "overshoot_flag": bool(any(abs(v) > 1.25 * abs(ceiling)
                                   for r in heat for v in r)) if ceiling else False,
        "positions_swept": positions,
        "position_tokens": [all_tok[p] for p in positions],
        "prompt_tokens": all_tok,
        "causal_heatmap_l_x_p": heat,              # nats
        "causal_heatmap_frac_of_ceiling": frac,    # 1.0 == full donor recovery
    }


def parity_check(model, model_id, tok, item, mode, device, dtype, tol=0.02):
    """Recompute base/donor diffs on CPU fp32. Abort if |delta| > tol nats."""
    import copy
    recipient = item["prompt"]
    donor, _, _ = build_donor(recipient, tok, mode)
    def diffs(m, dev):
        s, _, _ = score(m, tok, recipient, item["target_stale"], dev)
        r, _, _ = score(m, tok, recipient, item["target_recent"], dev)
        ds, _, _ = score(m, tok, donor, item["target_stale"], dev)
        dr, _, _ = score(m, tok, donor, item["target_recent"], dev)
        return (r - s), (dr - ds)
    a_base, a_don = diffs(model, device)
    cpu = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=torch.float32, low_cpu_mem_usage=True).eval()
    cpu.config.use_cache = False
    c_base, c_don = diffs(cpu, "cpu")
    del cpu
    d1, d2 = abs(a_base - c_base), abs(a_don - c_don)
    print(f"[parity] base: acc={a_base:+.4f} cpu={c_base:+.4f} |d|={d1:.4f}\n"
          f"[parity] donor: acc={a_don:+.4f} cpu={c_don:+.4f} |d|={d2:.4f}")
    ok = max(d1, d2) <= tol
    print(("[parity] PASS" if ok else f"[parity] FAIL (> {tol}) -> use --dtype fp32"))
    return {"passed": ok, "max_abs_delta_nats": round(max(d1, d2), 4),
            "acc_base": round(a_base, 4), "cpu_base": round(c_base, 4)}


def load_model(model_id, device, dtype_pref="auto"):
    """MPS fp32 on a 42-layer model OOMs / hits the storage-not-allocated bug.
    bf16 on MPS is allowed, but it BREAKS AD-series fp32 parity, so it is
    tagged in provenance and must be parity-checked (--parity_check)."""
    import torch
    if dtype_pref == "auto":
        dtype = torch.bfloat16 if device == "mps" else torch.float32
    else:
        dtype = {"fp32": torch.float32, "bf16": torch.bfloat16}[dtype_pref]

    def _load(dt):
        m = AutoModelForCausalLM.from_pretrained(
            model_id, torch_dtype=dt, low_cpu_mem_usage=True)  # NO device_map
        m.eval()
        m.config.use_cache = False
        return m

    m = _load(dtype)
    try:
        m = m.to(device)
    except (RuntimeError, MemoryError) as e:
        print(f"[!] {device}/{dtype} placement failed ({e}).")
        if device == "mps" and dtype != torch.bfloat16:
            print("[!] Retrying MPS in bfloat16.")
            del m
            dtype = torch.bfloat16
            m = _load(dtype).to(device)
        else:
            print("[!] Falling back to CPU fp32. Never silently use fp16.")
            device, dtype = "cpu", torch.float32
            del m
            m = _load(dtype)

    if device == "mps" and dtype == torch.bfloat16:
        print("[!] PARITY WARNING: bf16 on MPS. Logit diffs carry ~1e-2 nats of "
              "noise, comparable to the pilot's per-cell chatter. Results are "
              "NOT AD-series comparable until --parity_check passes.")
    print(f"[+] device={device} dtype={str(dtype).split('.')[-1]}")
    return m, device, dtype


def main():
    ap = argparse.ArgumentParser()
    ch = list(GEMMA_MODEL_CONFIGS.keys())
    ap.add_argument("--model_id", default=ch[0], choices=ch)
    ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    default_data_dir = Path(__file__).resolve().parent.parent / "data"
    default_dataset = str(default_data_dir / "conflict_dataset.json") if (default_data_dir / "conflict_dataset.json").exists() else "ai-ml/gemma-priority-probing/data/conflict_dataset.json"
    default_out = str(default_data_dir / "patching_results.json")
    ap.add_argument("--dataset", default=default_dataset)
    ap.add_argument("--out", default=default_out)
    ap.add_argument("--mode", default="authority", choices=["authority", "recency", "date_recency"])
    ap.add_argument("--dtype", default="auto", choices=["auto", "fp32", "bf16"])
    ap.add_argument("--all_positions", action="store_true")
    ap.add_argument("--keep_last", type=int, default=6)
    ap.add_argument("--parity_check", action="store_true",
                    help="Recompute base/donor diffs on CPU fp32 and abort if "
                         "|delta| > 0.02 nats vs the accelerator.")
    a = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(a.model_id)
    model, device, dtype = load_model(a.model_id, a.device, a.dtype)

    ds_path = Path(a.dataset if Path(a.dataset).exists() else "conflict_dataset.json").resolve()
    print(f"Loading dataset from: {ds_path}")
    items = [d for d in json.load(open(ds_path)) if d["id"].endswith("_conflict") or d["id"].endswith("_conflict_cb")]
    if not items:
        raise ValueError("No *_conflict items found. Baselines have identical targets "
                         "and will trip the F2 guard.")
    import hashlib
    for it in items:
        print(f"Prompt SHA8 for {it['id']}: {hashlib.sha256(it['prompt'].encode()).hexdigest()[:8]}")
    print(f"[+] {len(items)} conflict items | device={device} | dtype={dtype}")

    if a.parity_check:
        par = parity_check(model, a.model_id, tok, items[0], a.mode, device, str(dtype))
        if not par["passed"]:
            import sys
            sys.exit(1)
    else:
        par = None

    jl = GemmaJLens(model, tok, device=device, model_id=a.model_id)
    results, flips = {}, {}
    import time
    for it in items:
        recipient = it["prompt"]
        donor, marker, cand = build_donor(recipient, tok, a.mode)
        pos = None if a.all_positions else select_positions(
            recipient, tok,
            markers=[it.get("auth_marker"), it.get("recent_marker"), marker],
            entities=[it["target_stale"], it["target_recent"]],
            keep_last=a.keep_last)
        flips[it["id"]] = {"marker": marker, "flip_used": cand}
        print(f"\n[+] {it['id']} [{a.mode}]: '{marker}' -> '{cand}' | "
              f"{len(pos) if pos else 'all'} positions")
        t0 = time.time()
        results[it["id"]] = sweep(model, tok, jl, recipient, donor,
                                  it["target_stale"], it["target_recent"], device, a.chunk, a.mode, positions=pos)
        results[it["id"]]["wall_clock_s"] = round(time.time() - t0, 1)
        print(f"  wall-clock: {results[it['id']]['wall_clock_s']}s")

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump({"_provenance": {"model_id": a.model_id, "device": device,
                               "dtype": str(dtype).split('.')[-1], "mode": a.mode,
                               "n_items": len(items) // 4, "n_cells": len(items), "chunk": a.chunk, 
                               "flips": flips, "parity": par,
                               "note": "PILOT"},
               "results": results}, open(a.out, "w"), indent=2)
    print(f"\nWrote {a.out}")


if __name__ == "__main__":
    main()
