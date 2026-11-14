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

from pydantic import BaseModel, Field
from typing import List

class EvaluationScore(BaseModel):
    name: str = Field(description="The name of the scoring criteria category.")
    score: float = Field(description="The awarded score.")
    reasoning: str = Field(description="The reasoning behind this score.")

class EvaluationOutput(BaseModel):
    scores: List[EvaluationScore]
    total_score: float = Field(description="The total score summing up all category scores.")
    overall_comments: str = Field(description="Overall comments on the project.")
    confidence_score: float = Field(description="Score between 0.0 and 1.0 indicating confidence in the evaluation.")
