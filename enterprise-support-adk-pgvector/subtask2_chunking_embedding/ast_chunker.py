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
Subtask 2: Structural Markdown AST Heading-Aware Chunker.
Why this logic:
- Standard character/token window chunkers cut numbered steps in half and orphan resolutions from symptoms.
- An AST-based approach splits strictly at `#`, `##`, and `###` headers.
- Ancestor heading breadcrumbs are injected into each chunk so isolated vectors retain full context.
"""

import mistune

class HeadingAwareChunker:
    def __init__(self):
        self.markdown_parser = mistune.create_markdown(renderer=None)

    def chunk_document(self, doc_title: str, markdown_text: str) -> list[dict]:
        """
        Parses Markdown tokens into semantic sections with injected ancestor breadcrumbs.
        """
        tokens = self.markdown_parser.parse(markdown_text)[0]
        chunks = []
        
        current_ancestors = [doc_title]
        current_buffer = []

        for token in tokens:
            t_type = token.get("type")

            if t_type == "heading":
                # Flush the preceding block if it contains content
                if current_buffer:
                    chunks.append({
                        "hierarchy": " > ".join(current_ancestors),
                        "content": "\n".join(current_buffer).strip()
                    })
                    current_buffer = []

                level = token["attrs"]["level"]
                heading_text = "".join([c.get("raw", "") for c in token.get("children", [])])
                
                # Maintain heading stack depth (e.g. "[App: ZTNA Client] > [OS: Desktop]")
                if level <= len(current_ancestors):
                    current_ancestors = current_ancestors[:level]
                current_ancestors.append(heading_text)
            else:
                # Accumulate lists, paragraphs, code blocks
                raw_text = token.get("raw") or ""
                if raw_text:
                    current_buffer.append(raw_text)

        # Flush final buffer
        if current_buffer:
            chunks.append({
                "hierarchy": " > ".join(current_ancestors),
                "content": "\n".join(current_buffer).strip()
            })

        return chunks
