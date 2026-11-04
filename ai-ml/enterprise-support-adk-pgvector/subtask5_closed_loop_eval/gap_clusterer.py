# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Subtask 5: Semantic Gap Clusterer and Automatic Markdown Runbook Generator.
Why this logic:
- Transforms agent failures into actionable documentation fixes.
- When multiple users hit an unresolved problem, an LLM drafts an agent-ready Markdown runbook.
- Pings the Content Owner via Enterprise Chat, closing the documentation gap automatically.
"""

from vertexai.generative_models import GenerativeModel

class GapClusteringService:
    def __init__(self):
        self.model = GenerativeModel("gemini-2.5-flash")

    def synthesize_missing_runbook(self, cluster_topic: str, sample_questions: list[str]) -> str:
        """
        Generates an Agent-Ready KCS Markdown template prepopulated from telemetry logs.
        """
        prompt = f"""
        You are an IT Technical Writer. Create a standardized runbook based on these unresolved employee inquiries:
        Topic: {cluster_topic}
        User Queries: {sample_questions}

        Follow this exact schema:
        ---
        Target_Audience: All-Employees
        Last_Verified_Date: {self._today_str()}
        Content_Owner: @it-helpdesk
        ---
        # [Environment]: [Symptom / Question]
        ## Issue
        [Explain symptom quoting error messages]
        ## Resolution
        1. [Step 1]
           Expected result: [What user sees]
        """
        response = self.model.generate_content(prompt)
        return response.text

    def _today_str(self):
        from datetime import date
        return date.today().strftime("%Y-%m-%d")
