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

"""Evaluation contract shared by the judge runner and the agent.

Mirrors the fields parsed in agent/src/adapters/outbound/sandbox_direct.py.
"""

from pydantic import BaseModel, Field


class CriterionScore(BaseModel):
    name: str = Field(description="The criterion name exactly as written in criteria.md.")
    score: float = Field(description="Score on the criterion's scale, e.g. 1-10 or 1-5.")
    reasoning: str = Field(
        description=(
            "Detailed critique citing file paths relative to the repository root "
            "(e.g. src/App.tsx:42-43), function names or line numbers, including the results "
            "of any builds or tests you ran. Plain text paths only: no markdown links, "
            "file:// URIs or absolute /home/sandbox paths."
        )
    )


class Evaluation(BaseModel):
    scores: list[CriterionScore] = Field(description="One entry per criterion in criteria.md.")
    total_score: float = Field(description="Sum or calculated average as dictated by criteria.md.")
    overall_comments: str = Field(
        description="Holistic summary of engineering quality, documentation accuracy and execution."
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="0.0-1.0: how confidently you could review, build or verify the codebase.",
    )
