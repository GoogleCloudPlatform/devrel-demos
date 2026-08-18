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

import random
import os

templates = [
    "Context:\n[OFFICIAL GUIDELINE (2019)]\nThe mandatory core framework for {task} is {stale}.\n\n[Team Update (Yesterday)]\nWe have migrated all frameworks. The new framework is {recent}.\n\nQuestion: What framework should I use for {task}?\nAnswer:",
    "Context:\n[ENTERPRISE ARCHITECTURE SPECIFICATION (2020)]\nThe authoritative {resource} is {stale}.\n\n[Slack Note (2 hours ago)]\nDeprecating old ones today. The active {resource} is {recent}.\n\nQuestion: Which {resource} should I use?\nAnswer:",
    "Context:\n[Old Wiki Page]\nFor {action}, please use {stale} moving forward.\n\n[Meeting Notes (Today)]\nWe decided to switch to {recent} for {action}.\n\nQuestion: What should I use for {action}?\nAnswer:",
    "Context:\n[Policy Doc 2021]\nThe default tool for {process} is {stale}.\n\n[Recent Email]\nWe are standardizing on {recent} for {process}.\n\nQuestion: Which tool is the standard for {process}?\nAnswer:"
]

tasks = ["project planning", "deployment", "testing", "monitoring", "CI/CD", "data analysis", "ML training", "UI development", "backend routing", "caching"]
resources = ["database endpoint", "API gateway", "cache server", "logging cluster", "auth provider", "message queue", "search index"]
actions = ["submitting tickets", "onboarding users", "provisioning servers", "running backups", "generating reports", "managing secrets"]
processes = ["code review", "incident response", "release management", "vulnerability scanning", "dependency tracking"]

entities = ["GCP", "Cloud", "AWS", "Azure", "telemetry", "metrics", "kafka", "rabbitmq", "postgres", "mysql", "redis", "memcached", "vault", "berglas", "jira", "asana", "jenkins", "gitlab", "datadog", "splunk"]

out_file = "/path/to/your/project.txt"
seen = set()
prompts = []

random.seed(42)

def add_prompt(p):
    if p not in seen:
        seen.add(p)
        prompts.append(p)

# Generate variations
while len(prompts) < 160: # 80% task-specific
    template = random.choice(templates)
    
    # Pick stale and recent that are different
    stale = random.choice(entities)
    recent = random.choice(entities)
    while stale == recent:
        recent = random.choice(entities)
        
    if "{task}" in template:
        p = template.format(task=random.choice(tasks), stale=stale, recent=recent)
    elif "{resource}" in template:
        p = template.format(resource=random.choice(resources), stale=stale, recent=recent)
    elif "{action}" in template:
        p = template.format(action=random.choice(actions), stale=stale, recent=recent)
    elif "{process}" in template:
        p = template.format(process=random.choice(processes), stale=stale, recent=recent)
    else:
        continue
        
    # Hold out scenario_01
    if ("project planning" in p or "GCP" in p or "Cloud" in p):
        if stale in ["GCP", "Cloud"] and recent in ["GCP", "Cloud"]:
            continue # holdout scenario_01
            
    add_prompt(p)

# Add generic text for coverage (20%)
generics = [
    "The quick brown fox jumps over the lazy dog.",
    "Machine learning models often require significant computational resources.",
    "Cloud computing has revolutionized how we build and deploy applications.",
    "A well-designed API is crucial for system integration.",
    "Data privacy laws are becoming more strict globally.",
    "Open source software powers much of the modern internet.",
    "Continuous integration helps catch bugs early in development.",
    "Microservices architecture provides better scalability.",
    "Kubernetes is a popular container orchestration platform.",
    "Python is widely used in data science and AI."
]
while len(prompts) < 200:
    add_prompt(random.choice(generics) + " " + random.choice(generics))

with open(out_file, "w") as f:
    for p in prompts:
        f.write(p.replace('\n', ' ') + '\n')

print(f"Generated {len(prompts)} unique prompts to {out_file}")
