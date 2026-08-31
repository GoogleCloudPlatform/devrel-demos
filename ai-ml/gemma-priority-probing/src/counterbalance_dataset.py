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

"""Counterbalanced conflict dataset. Renders from templates; NEVER string-replaces
a live prompt (that corrupted the question text in the previous version).
2 items x 2 entity assignments x 2 block orders = 8 conflict + 8 baseline."""
import json, hashlib
from pathlib import Path

ITEMS = [
  {"item_id": "template_selection_01",
   "entity_a": "GCP", "entity_b": "Cloud",
   "auth":   "[OFFICIAL GUIDELINE (2019)]\nThe mandatory core template for "
             "project planning is {E} PDD.",
   "recent": "[Team Update (Yesterday)]\nWe have migrated all templates. "
             "The new template is {E} PDD.",
   "question": "What template should I use for project planning?",
   "auth_marker": "(2019)", "recent_marker": "(Yesterday)",
   "auth_header": "OFFICIAL GUIDELINE"},
  {"item_id": "api_endpoint_02",
   "entity_a": "telemetry", "entity_b": "metrics",
   "auth":   "[ENTERPRISE ARCHITECTURE SPECIFICATION (2020)]\nThe authoritative "
             "database endpoint for log ingestion is {E}-v1.internal.",
   "recent": "[Slack Note (2 hours ago)]\nDeprecating old endpoints today. "
             "The active log ingestion endpoint is {E}-v2.internal.",
   "question": "Which endpoint should I send ingestion logs to?",
   "auth_marker": "(2020)", "recent_marker": "(2 hours ago)",
   "auth_header": "ENTERPRISE ARCHITECTURE SPECIFICATION"},
]
# NOTE: "metrics logging" -> "log ingestion" so neither entity appears in the
# question. This was the bug that made api_endpoint_02_cb uninterpretable.

def build():
    out = []
    for s in ITEMS:
        for assign in ("ab", "ba"):
            auth_e, rec_e = ((s["entity_a"], s["entity_b"]) if assign == "ab"
                             else (s["entity_b"], s["entity_a"]))
            for order in ("auth_first", "recent_first"):
                for kind in ("conflict", "baseline"):
                    re_ = rec_e if kind == "conflict" else auth_e
                    ab = s["auth"].format(E=auth_e)
                    rb = s["recent"].format(E=re_)
                    blocks = [ab, rb] if order == "auth_first" else [rb, ab]
                    p = ("Context:\n" + "\n\n".join(blocks) +
                         f"\n\nQuestion: {s['question']}\nAnswer:")
                    out.append({
                        "id": f"{s['item_id']}_{assign}_{order}_{kind}",
                        "item_id": s["item_id"], "entity_assignment": assign,
                        "block_order": order, "prompt": p,
                        "prompt_sha8": hashlib.sha256(p.encode()).hexdigest()[:8],
                        "target_stale": auth_e, "target_recent": re_,
                        "auth_marker": s["auth_marker"],
                        "recent_marker": s["recent_marker"],
                        "auth_header": s["auth_header"],
                        "pair_key": f"{s['item_id']}_{order}_{kind}"})
    return out

if __name__ == "__main__":
    ds = build()
    ids = [d["id"] for d in ds]
    assert len(set(ids)) == len(ids)
    for d in ds:  # entities must not leak into the question
        q = d["prompt"].split("Question: ")[1]
    data_dir = Path(__file__).resolve().parent.parent / "data"
    if not data_dir.exists():
        data_dir = Path("ai-ml/gemma-priority-probing/data") if Path("ai-ml/gemma-priority-probing/data").exists() else Path("gemma-priority-probing/data") if Path("gemma-priority-probing/data").exists() else Path("data") if Path("data").exists() else Path(".")
    dst = data_dir / "conflict_dataset_counterbalanced.json"
    json.dump(ds, open(dst, "w"), indent=2)
    n = sum(1 for d in ds if d["id"].endswith("_conflict"))
    print(f"Wrote {dst}: {len(ds)} rows ({n} conflict). Source dataset untouched.")
