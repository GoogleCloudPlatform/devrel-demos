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

# src/core/models/message.py
from pydantic import BaseModel, Field
from typing import List, Optional

class ScoringCriteria(BaseModel):
    name: str
    description: str = ""
    weight: float = 1.0
    max_score: float = 10.0

class AgentRequest(BaseModel):
    """The incoming task from the backend (Judging Task)"""
    task_id: str
    project_name: str
    github_url: str
    submission_text: str
    judging_rubric: str
    scoring_criteria: List[ScoringCriteria]

class CategoryScore(BaseModel):
    name: str
    score: float
    reasoning: str
    max_score: float = 10.0
    weight: float = 1.0

class AgentResponse(BaseModel):
    """The result sent back to the backend (Judging Result)"""
    task_id: str
    status: str = Field(description="'success' or 'error'")
    error_message: Optional[str] = None
    scores: List[CategoryScore] = []
    total_score: float = 0.0
    overall_comments: str = ""
    confidence_score: float = 0.0
