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

# src/adapters/outbound/adk_agent.py
from src.core.ports.agent_service import AgentService
from src.core.models.message import AgentRequest, AgentResponse, CategoryScore
from src.core.models.evaluation import EvaluationOutput
import logging

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from .shared_sandbox import evaluate_repository

logger = logging.getLogger(__name__)

class ADKAgentAdapter(AgentService):
    def __init__(self):
        self.agent = Agent(
            name="hackathon_judge",
            model="gemini-3-flash-preview",
            instruction="""
You are an expert hackathon judge evaluating a project.
Analyze the provided submission and evaluate it against the given criteria and rubric.
Be highly objective and provide detailed reasoning for each score.

You must use the `evaluate_repository` tool to delegate the deep codebase analysis to a sandboxed agent.
Pass the GitHub URL and the scoring criteria formatted as markdown to the tool.
The tool will return a JSON string with the evaluation results. Use this data to formulate your final response.
            """,
            tools=[evaluate_repository],
            output_schema=EvaluationOutput,
            output_key="evaluation_result",
        )
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=self.agent,
            app_name="hackathon_judge_app",
            session_service=self.session_service
        )

    async def process_message(self, request: AgentRequest) -> AgentResponse:
        try:
            # Format criteria
            criteria_text = "\n".join([f"- {c.name} (Weight: {c.weight}, Max Score: {c.max_score}): {c.description}" for c in request.scoring_criteria])
            
            prompt = f"""
Project Name: {request.project_name}
GitHub URL: {request.github_url}

Submission Description:
{request.submission_text}

Judging Rubric:
{request.judging_rubric}

Scoring Criteria:
{criteria_text}

Please evaluate this project and provide scores for each category.
"""
            session_id = f"session_{request.task_id}"
            user_id = "system"
            
            await self.session_service.create_session(
                app_name="hackathon_judge_app", 
                user_id=user_id, 
                session_id=session_id
            )

            # Run the agent
            async for _ in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])
            ):
                pass
                
            session = await self.session_service.get_session(app_name="hackathon_judge_app", user_id=user_id, session_id=session_id)
            eval_output_dict = session.state.get("evaluation_result")
            
            if not eval_output_dict:
                return AgentResponse(
                    task_id=request.task_id,
                    status="error",
                    error_message="Agent failed to produce evaluation_result in state."
                )
                
            # Parse output
            if isinstance(eval_output_dict, EvaluationOutput):
                eval_output = eval_output_dict
            else:
                eval_output = EvaluationOutput.model_validate(eval_output_dict)
            
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
            import traceback
            traceback.print_exc()
            return AgentResponse(
                task_id=request.task_id,
                status="error",
                error_message=str(e)
            )
