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

"""
Dataset Curation for Authority vs. Recency Bias Conflict Prompts.
Generates structured prompt pairs and permutations for J-Space probing.
"""

import json
from pathlib import Path

DATASET = [
    {
        "id": "template_selection_01",
        "category": "planning_template",
        "doc_stale": {
            "title": "OFFICIAL GUIDELINE (2019)",
            "content": "The mandatory core template for project planning is GCP PDD.",
            "target_token": "GCP",
            "authority_marker": "OFFICIAL GUIDELINE",
            "year": 2019
        },
        "doc_recent": {
            "title": "Team Update (Yesterday)",
            "content": "We have migrated all templates. The new template is Cloud PDD.",
            "target_token": "Cloud",
            "authority_marker": "Team Update",
            "year": 2026
        },
        "question": "What template should I use for project planning?",
        "answer_stale": "GCP PDD",
        "answer_recent": "Cloud PDD"
    },
    {
        "id": "api_endpoint_02",
        "category": "infrastructure_api",
        "doc_stale": {
            "title": "ENTERPRISE ARCHITECTURE SPECIFICATION (2020)",
            "content": "The authoritative database endpoint for metrics logging is telemetry-v1.internal.",
            "target_token": "telemetry",
            "authority_marker": "ENTERPRISE ARCHITECTURE SPECIFICATION",
            "year": 2020
        },
        "doc_recent": {
            "title": "Slack Note (2 hours ago)",
            "content": "Deprecating old endpoints today. The active metrics logging endpoint is metrics-v2.internal.",
            "target_token": "metrics",
            "authority_marker": "Slack Note",
            "year": 2026
        },
        "question": "Which endpoint should I send metrics logs to?",
        "answer_stale": "telemetry-v1.internal",
        "answer_recent": "metrics-v2.internal"
    },
    {
        "id": "deployment_zone_03",
        "category": "cloud_config",
        "doc_stale": {
            "title": "GLOBAL DEPLOYMENT POLICY (2021)",
            "content": "All production services must be deployed in us-central1.",
            "target_token": "us-central1",
            "authority_marker": "GLOBAL DEPLOYMENT POLICY",
            "year": 2021
        },
        "doc_recent": {
            "title": "Hotfix Email (10 mins ago)",
            "content": "us-central1 is experiencing outages. Route all production deployments to us-east4.",
            "target_token": "us-east4",
            "authority_marker": "Hotfix Email",
            "year": 2026
        },
        "question": "Where should I deploy production services?",
        "answer_stale": "us-central1",
        "answer_recent": "us-east4"
    }
]

def format_prompt(doc_first, doc_second, question):
    return (
        f"Context:\n"
        f"[{doc_first['title']}]\n{doc_first['content']}\n\n"
        f"[{doc_second['title']}]\n{doc_second['content']}\n\n"
        f"Question: {question}\n"
        f"Answer:"
    )

def generate_full_dataset():
    prompts = []
    for item in DATASET:
        # Permutation 1: Stale Doc First, Recent Doc Second
        prompt_stale_first = format_prompt(item["doc_stale"], item["doc_recent"], item["question"])
        prompts.append({
            "id": f"{item['id']}_stale_first",
            "item_id": item["id"],
            "order": "stale_first",
            "prompt": prompt_stale_first,
            "target_stale": item["doc_stale"]["target_token"],
            "target_recent": item["doc_recent"]["target_token"]
        })
        
        # Permutation 2: Recent Doc First, Stale Doc Second (Control for position bias)
        prompt_recent_first = format_prompt(item["doc_recent"], item["doc_stale"], item["question"])
        prompts.append({
            "id": f"{item['id']}_recent_first",
            "item_id": item["id"],
            "order": "recent_first",
            "prompt": prompt_recent_first,
            "target_stale": item["doc_stale"]["target_token"],
            "target_recent": item["doc_recent"]["target_token"]
        })

    return prompts

def main():
    output_path = Path("conflict_dataset.json")
    prompts = generate_full_dataset()
    with open(output_path, "w") as f:
        json.dump(prompts, f, indent=2)
    print(f"Generated {len(prompts)} conflict prompts and saved to {output_path.resolve()}")

if __name__ == "__main__":
    main()
