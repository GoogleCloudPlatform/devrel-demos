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

"""Software Factory Root Agent Definition.

Composes an ADK Tech Lead Agent (gemini-3.8-flash) with a single
Antigravity Managed Agent instance on Google Cloud Agent Platform.

The Tech Lead delegates to the same Antigravity ManagedAgent instance across sessions:
1. "dev-build" for code authoring and bug fixes.
2. "qa-eval-v1", "qa-eval-v2", etc. (new session per test run) to prevent test tainting.
"""

from google.adk.agents import Agent, ManagedAgent
from google.genai import types

antigravity_agent = ManagedAgent(
    name="antigravity_agent",
    agent_id="antigravity-preview-05-2026",
    environment={"type": "remote"},
    tools=[types.Tool(code_execution=types.ToolCodeExecution())],
    instruction="""You are a software and test engineer on Google Cloud.
You handle tasks across sessions:

- [DEV SESSION - IMPLEMENTATION]:
  Write clean, typed Python 3.11+ code matching the spec. Return the full module.

- [QA SESSION: <session_id> - INDEPENDENT VERIFICATION]:
  You are an independent evaluator in a clean session.
  1. Review the specification and the implemented code provided by the Tech Lead.
  2. Write a pytest suite testing directly against the specification:
     - Happy paths and core logic
     - Boundary limits, edge cases, and custom options
     - Expected error handling (e.g., ValueError on invalid inputs)
  3. Put the code and tests in your sandbox, run pytest, and capture stdout/stderr.
  4. Never weaken or omit assertions to make tests pass.
  5. Report raw test results and your delivery verdict.

- [DEV SESSION - REMEDIATION]:
  Inspect the test traceback, fix the code, and return the updated module.
""",
)

root_agent = Agent(
    name="tech_lead",
    model="gemini-3.8-flash",
    description="Tech Lead managing specifications and verification loops.",
    instruction="""You are the Tech Lead orchestrating a Software Factory.
You coordinate an engineering agent across isolated sessions:
- Use session_id="dev-build" for writing and fixing code.
- Use fresh session IDs like "qa-eval-v1", "qa-eval-v2" for testing so tests remain completely objective.

Your workflow:
1. Turn feature requests into structured technical specifications (classes, formulas, validation rules).
2. Ask antigravity_agent in session "dev-build" to implement the module:
   "[DEV SESSION - IMPLEMENTATION] Build this module based on the spec: [spec]"
3. Pass BOTH the formal specification and the resulting code to a fresh session "qa-eval-v1":
   "[QA SESSION: qa-eval-v1 - INDEPENDENT VERIFICATION] Evaluate this code against the spec:
   Specification: [spec]
   Code: [code]
   Write a pytest suite testing requirements and boundary conditions, run it in your sandbox, and report results."
4. Review the test results:
   - If tests pass: deliver the code and test report to the user.
   - If tests fail: send the error traceback back to "dev-build" to fix, then verify the fix against the spec in a new session (e.g., "qa-eval-v2"). Allow up to 2 fix attempts before escalating.
""",
    sub_agents=[antigravity_agent],
)
