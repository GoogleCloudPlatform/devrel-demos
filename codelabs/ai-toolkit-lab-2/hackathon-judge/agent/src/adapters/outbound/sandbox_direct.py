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

# agent/src/adapters/outbound/sandbox_direct.py
import json
import logging
import traceback
import asyncio

from src.core.models.evaluation import EvaluationOutput
from src.core.models.message import AgentRequest, AgentResponse, CategoryScore
from src.core.ports.agent_service import AgentService
from pydantic import ValidationError
from .shared_sandbox import evaluate_repository

logger = logging.getLogger(__name__)

class SandboxDirectAdapter(AgentService):
    async def process_message(self, request: AgentRequest) -> AgentResponse:
        try:
            # Format criteria
            criteria_text = "\n".join([f"- {c.name} (Weight: {c.weight}, Max Score: {c.max_score}): {c.description}" for c in request.scoring_criteria])
            
            judging_criteria = f"""
Project Name: {request.project_name}
GitHub URL: {request.github_url}

Submission Description:
{request.submission_text}

Judging Rubric:
{request.judging_rubric}

Scoring Criteria:
{criteria_text}
"""
            result_json = await asyncio.to_thread(evaluate_repository, request.github_url, judging_criteria)
            
            try:
                eval_output_dict = json.loads(result_json)
                if "error" in eval_output_dict:
                    logger.error(f"Sandbox returned an error: {eval_output_dict['error']}")
                    return AgentResponse(
                        task_id=request.task_id,
                        status="error",
                        error_message=eval_output_dict['error']
                    )
                eval_output = EvaluationOutput.model_validate(eval_output_dict)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"Failed to parse sandbox output: {result_json}")
                return AgentResponse(
                    task_id=request.task_id,
                    status="error",
                    error_message=f"Failed to parse sandbox output: {e}"
                )

            # Create lookups for max scores and weights
            max_score_lookup = {c.name: c.max_score for c in request.scoring_criteria}
            weight_lookup = {c.name: c.weight for c in request.scoring_criteria}
            
            # Map to response schema
            category_scores = [
                CategoryScore(
                    name=s.name, 
                    score=s.score, 
                    reasoning=s.reasoning,
                    max_score=max_score_lookup.get(s.name, 10.0),
                    weight=weight_lookup.get(s.name, 1.0)
                )
                for s in eval_output.scores
            ]
            
            return AgentResponse(
                task_id=request.task_id,
                status="success",
                scores=category_scores,
                total_score=eval_output.total_score,
                overall_comments=eval_output.overall_comments,
                confidence_score=eval_output.confidence_score
            )
            
        except Exception as e:
            traceback.print_exc()
            return AgentResponse(
                task_id=request.task_id,
                status="error",
                error_message=str(e)
            )
