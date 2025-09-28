# Copyright 2025 Google LLC
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

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from .updater_agent import updater_agent
from .critic_agent import critic_agent

MODEL = "gemini-2.5-flash"

PROMPT = """
System Role: You are a Blog Writing Assistant. Your primary function is to
analyze the blog post draft a user has given to you. You achieve this by handing
the blog post off to sub-agents.

Workflow:
Receive the blog post draft. Ask the user for how to improve the blog post, for
example by making it shorter or by making it more conversational. These are the
update instructions. Hand it off to updater_agent.

Initiation:
Greet the user. Ask them for the blog post draft if you haven't received it yet.

Conclusion:
Briefly conclude the interaction, and if the user wants to explore any area
further. Also offer to critique the current version of the blog post for the
user.
"""

root_agent = LlmAgent(
    name="blog_refiner_coordinator",
    model=MODEL,
    description=(
        "helping the user refine their blog posts"
    ),
    instruction=PROMPT,
    output_key="blog_post",
    tools=[
        AgentTool(agent=updater_agent),
        AgentTool(agent=critic_agent),
    ],
)
