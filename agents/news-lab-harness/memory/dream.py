#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Dreaming routine (`memory/dream.py`) for the Breaking News Lab harness.

Consolidates raw session notes from `scratchpad` in `memory/memory_graph.json`:
1. Promotes verified notes (`verified: true` from non-rumor-mill sources) into permanent graph `nodes`.
2. Creates `edges` connecting new facts to existing entities in the graph.
3. Prunes unverified rumors or notes from `known_rumor_mills` so they never pollute future sessions.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_GRAPH_PATH = Path(__file__).resolve().parent / "memory_graph.json"


def dream(graph_path: Path = DEFAULT_GRAPH_PATH, dry_run: bool = False) -> Dict[str, Any]:
    """Run one dreaming consolidation cycle over the memory graph."""
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes: List[Dict[str, Any]] = data.get("nodes", [])
    edges: List[Dict[str, Any]] = data.get("edges", [])
    scratchpad: List[Dict[str, Any]] = data.get("scratchpad", [])
    rumor_mills = {s.lower() for s in data.get("known_rumor_mills", [])}
    verified_sources = set(data.get("verified_sources", []))

    existing_claims = {n["claim"].strip().lower(): n["id"] for n in nodes}
    entity_to_ids: Dict[str, List[str]] = {}
    for n in nodes:
        entity_to_ids.setdefault(n["entity"].strip().lower(), []).append(n["id"])

    promoted: List[Dict[str, Any]] = []
    pruned: List[Dict[str, Any]] = []

    for item in scratchpad:
        claim = str(item.get("claim", "")).strip()
        entity = str(item.get("entity", "General")).strip()
        source = str(item.get("source", "Unknown")).strip()
        is_verified = bool(item.get("verified", False))

        if not claim or not is_verified or source.lower() in rumor_mills:
            pruned.append(item)
            continue

        if claim.lower() in existing_claims:
            continue

        new_id = f"fact_{len(nodes) + 1:03d}"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        node = {
            "id": new_id,
            "entity": entity,
            "claim": claim,
            "source": source,
            "confidence": 1.0 if source in verified_sources else 0.85,
            "added_at": now_iso,
        }
        nodes.append(node)
        promoted.append(node)
        existing_claims[claim.lower()] = new_id

        prior_ids = entity_to_ids.get(entity.lower(), [])
        if prior_ids:
            edges.append({"from": prior_ids[-1], "to": new_id, "relation": "updates_entity"})
        elif len(nodes) > 1:
            edges.append({"from": nodes[-2]["id"], "to": new_id, "relation": "related_finding"})
        entity_to_ids.setdefault(entity.lower(), []).append(new_id)

        if source and source not in verified_sources:
            data.setdefault("verified_sources", []).append(source)
            verified_sources.add(source)

    data["nodes"] = nodes
    data["edges"] = edges
    data["scratchpad"] = []
    data["last_dream_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not dry_run:
        graph_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    return {
        "promoted_count": len(promoted),
        "pruned_count": len(pruned),
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "promoted": promoted,
        "pruned": pruned,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Breaking News Lab memory dreaming loop.")
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH, help="Path to memory_graph.json")
    parser.add_argument("--dry-run", action="store_true", help="Preview consolidation without writing")
    args = parser.parse_args()

    summary = dream(graph_path=args.graph, dry_run=args.dry_run)
    print(
        f"Breaking News Lab Dreaming [COMPLETE] — "
        f"Promoted: {summary['promoted_count']} | Pruned Rumors: {summary['pruned_count']} | "
        f"Graph Size: {summary['total_nodes']} nodes, {summary['total_edges']} edges"
    )
    for node in summary["promoted"]:
        print(f"  + Promoted [{node['id']}] ({node['entity']}): {node['claim']} [Source: {node['source']}]")
    for bad in summary["pruned"]:
        print(f"  - Pruned unverified rumor ({bad.get('source', 'unknown')}): {bad.get('claim', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
