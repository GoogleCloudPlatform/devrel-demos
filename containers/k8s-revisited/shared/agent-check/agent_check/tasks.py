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

"""Load and validate agent-check task files."""
from dataclasses import dataclass, field

import yaml

REQUIRED = ("id", "spec", "checks")


@dataclass
class Task:
    id: str
    title: str
    spec: str
    checks: list
    conditions: list = field(default_factory=lambda: ["bare", "context_skill", "repair_loop"])
    runs_per_condition: int = 10


def load_tasks(path):
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a list of tasks")
    tasks = []
    for i, item in enumerate(data):
        missing = [k for k in REQUIRED if k not in item]
        if missing:
            raise ValueError(f"{path}: task {i} is missing {', '.join(missing)}")
        tasks.append(Task(
            id=item["id"],
            title=item.get("title", item["id"]),
            spec=item["spec"].strip(),
            checks=item["checks"],
            conditions=item.get("conditions", ["bare", "context_skill", "repair_loop"]),
            runs_per_condition=int(item.get("runs_per_condition", 10)),
        ))
    return tasks
