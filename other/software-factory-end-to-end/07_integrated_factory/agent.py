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

"""Step 5: Integrated Software Factory Architecture.

Orchestrates the Tech Lead Agent (gemini-3.8-flash) with the Antigravity
Managed Agent across distinct, isolated sessions:
- "dev-build": Retains patch context for authoring and remediating code.
- "qa-eval-v1", "qa-eval-v2": Fresh sessions per test run to prevent assertion softening.
"""

from google.adk.agents import Agent, ManagedAgent
from google.genai import types

# Configure the Antigravity Managed Agent.
# In the Gemini Agent Environment, 'environment' specifies the remote sandbox container / filesystem,
# while the session header (e.g., [DEV SESSION: dev-build] vs [QA SESSION: qa-eval-v1]) defines
# the prompt context. By using the same persistent environment (e.g. environment_id or named environment),
# the files on disk (like barista.py) are preserved across interactions, while fresh sessions provide
# an unbiased prompt context with zero memory of dev trade-offs.
antigravity_agent = ManagedAgent(
    name="antigravity_agent",
    agent_id="antigravity-preview-05-2026",
    environment={"type": "remote", "id": "factory-shared-env"},
    tools=[types.Tool(code_execution=types.ToolCodeExecution())],
    instruction="""You are a software and test engineer on Google Cloud working in a persistent remote sandbox.
All sessions share the same remote environment filesystem. You handle tasks across sessions:

- [DEV SESSION - IMPLEMENTATION]:
  Read the formal specification and write clean, typed Python 3.11+ code directly to the environment file (e.g., barista.py). Return confirmation and module summary.

- [QA SESSION: <session_id> - INDEPENDENT VERIFICATION]:
  You are an independent QA evaluator operating in a fresh, unbiased session.
  1. Review the formal specification provided by the Tech Lead.
  2. Write an objective pytest test suite (e.g., test_barista.py) directly against the specification:
     - Happy paths and core business logic
     - Boundary limits, edge cases, and custom configurations
     - Expected error handling (e.g., ValueError on invalid inputs)
  3. Execute pytest against the existing implementation file in the shared environment without altering the implementation.
  4. Never weaken or omit assertions to make tests pass.
  5. Report test stdout/stderr, pass/fail status, and your delivery verdict.

- [DEV SESSION - REMEDIATION]:
  You are the developer fixing bugs in your implementation session.
  Inspect the test traceback, fix the code in the implementation file (e.g., barista.py), and re-verify.
""",
)

root_agent = Agent(
    name="tech_lead",
    model="gemini-3.8-flash",
    description="Tech Lead managing specifications and verification loops.",
    instruction="""You are the Tech Lead orchestrating a Software Factory.
You coordinate an engineering agent across isolated sessions sharing a persistent environment:
- Use session_id="dev-build" for writing and fixing code in the shared environment (retains development memory).
- Maintain an evaluation loop counter: initialize loop_count = 1.
- For EVERY test verification round, ALWAYS increment and use a brand new session_id="qa-eval-v{loop_count}" (e.g., "qa-eval-v1", "qa-eval-v2", "qa-eval-v3"). Each tester session MUST start completely FRESH with zero prior context or bias.

Your workflow:
1. Turn feature requests into structured technical specifications (classes, formulas, validation rules).
2. Ask antigravity_agent in session "dev-build" to implement the module in the shared environment:
   "[DEV SESSION - IMPLEMENTATION] Build this module based on the spec and write it to the environment file (e.g., barista.py): [spec]"
3. Initialize loop_count = 1. Pass the formal specification to a fresh tester session "qa-eval-v{loop_count}":
   "[QA SESSION: qa-eval-v{loop_count} - INDEPENDENT VERIFICATION] Evaluate the implementation in the shared environment against this specification:
   Specification: [spec]
   Write an independent pytest suite (test_barista.py) testing requirements and boundary conditions against the existing barista.py in the environment, run pytest, and report results."
4. Review the test results:
   - If tests pass: deliver the code and test report to the user.
   - If tests fail:
     a. Send the test failure traceback back to "dev-build" to fix in barista.py.
     b. Increment loop_count += 1.
     c. Launch verification in a brand new session_id="qa-eval-v{loop_count}" with only the spec, ensuring the tester starts fresh with no memory of prior test runs.
     d. Allow up to 2 fix attempts (loop_count <= 3) before escalating to the user.
""",
    sub_agents=[antigravity_agent],
)
