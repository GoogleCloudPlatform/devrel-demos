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

from google.adk import Agent

MODEL = "gemini-2.5-flash"

PROMPT = """
Role: You are an AI critiquer of blog posts.

Read this blog post draft '{blog_post}'.

Propose 3 ways to improve the blog post, paying special attention to
- Clear and concise language.
- Why the reader should be interested.
- Be clear about prior knowledge needed.
- Short paragraphs.
- Subheadings (##) to break up logical sections.
- Bulleted or numbered lists for steps or key points.
- Bolding to highlight key terms and conclusions.
- A good hook in the beginning of the post.
- A call to action at the end of the post.

Make each suggestion 3-4 sentences long.
"""

critic_agent = Agent(
    model=MODEL,
    name="critic_agent",
    instruction=PROMPT,
    output_key="blog_post"
)
