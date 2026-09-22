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

"""Step 4: Standalone Antigravity Managed Agent.

Connects directly to the Google Cloud hosted Antigravity agent
(`antigravity-preview-05-2026`) with remote code execution sandbox enabled.
"""

from google.adk.agents import ManagedAgent
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
  1. Write a pytest suite for happy paths and edge cases.
  2. Put the code and tests in your sandbox, run pytest, and capture stdout/stderr.
  3. Never weaken or omit assertions to make tests pass.
  4. Report test results and your delivery verdict.

- [DEV SESSION - REMEDIATION]:
  Inspect the test traceback, fix the code, and return the updated module.
""",
)

# Expose as root_agent to inspect and interact with the managed agent standalone
root_agent = antigravity_agent
