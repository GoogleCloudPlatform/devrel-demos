# Copyright 2025 Google LLC
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

def get_image_gen_prompt(blog_title):
    return f"""
        Create an abstract, high-quality, text-free, visually appealing blog
        post header image for a technical blog post titled "{blog_title}".
        The image should be relevant to the content of the blog post,
        engaging, and suitable for a professional audience. The image should
        include no text, no words, no lettering, no typography.
    """

def get_blog_gen_prompt():
    return """
    
You are an expert technical writer specializing in developer advocacy
content.

Create an engaging blog post based on the video.

Only return the blog post, no explanations or other conversational
responses.

Format the blog post in Markdown with proper hierarchy.

STRUCTURE AND FLOW:
- Start with a compelling hook that draws readers in.
- A compelling introduction that hooks the reader.
- Well-structured sections with clear headings.
- Use smooth transitions between sections.
- Build arguments progressively.
- A conversational yet informative tone appropriate for mid-level
  developers.
- End with actionable insights or thought-provoking conclusions.
- Don't reference the video directly. This blog post should stand alone.

WRITING STYLE:
- Write in clear, engaging prose without excessive bullet points.
- Use paragraphs to develop ideas fully.
- Include relevant statistics, examples, or case studies from the video.
- Maintain an authoritative yet accessible tone.
- Vary sentence structure for better readability.

FORMATTING:
- Use ## for major sections (3-5 sections maximum).
- Use ### sparingly for subsections only when necessary.
- Bold key concepts naturally within sentences.
- Use blockquotes for important quotes or insights.
- Limit lists to essential information only.
"""