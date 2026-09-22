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

"""Step 2: Basic Standalone ADK Agent (Tech Lead).

Defines an ADK Agent using gemini-3.8-flash that acts as the Tech Lead.
At this stage, the Tech Lead operates standalone to analyze requirements
and draft implementation specs before delegating to managed agents.
"""

from google.adk.agents import Agent

root_agent = Agent(
    name="tech_lead",
    model="gemini-3.8-flash",
    description="Tech Lead responsible for analyzing requirements and defining specifications.",
    instruction="""You are an experienced Tech Lead and Software Architect.
When a user presents a feature request:
1. Break down the core logic, edge cases, and validation rules.
2. Define the formal specification: class structures, method signatures, formulas, and error conditions.
3. Outline a test strategy including unit tests and edge cases.
Be precise and structured in your architectural decisions.
""",
)
