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

# Configure the Antigravity Managed Agent.
# In the Gemini Agent Environment, the 'environment' parameter accepts 3 forms:
# 1. "remote" - Provision a fresh sandbox.
# 2. Environment ID (e.g. "factory-shared-env") - Reuse an existing sandbox with all files preserved.
# 3. Config object (e.g. {"type": "remote"}) - Provision a new sandbox with configuration.
# On this first provisioning occasion, we use a config object.
antigravity_agent = ManagedAgent(
    name="antigravity_agent",
    agent_id="antigravity-preview-05-2026",
    environment={"type": "remote"},
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

# Expose as root_agent to inspect and interact with the managed agent standalone
root_agent = antigravity_agent
