// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package prompts

import (
	"context"
	"fmt"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const expandPrompt = `Act as an expert technical writer. I need you to expand the work-in-progress article currently in your context into a comprehensive, helpful article that aligns with our "cozy web" editorial guidelines.

When expanding, your goal is to add depth, context, and utility without adding "fluff". Every new sentence must add value.

**Key Expansion Tasks:**
1.  **Context & Definitions:** Assume the reader is smart but lacks specific context. Briefly explain complex terms or provide helpful analogies.
2.  **Citations & Resources (CRITICAL):** You MUST actively identify every tool, library, protocol, or official documentation mentioned in the text and add a markdown link to its official source. Don't just say "check the docs"; provide the specific URL.
3.  **Code & Examples:** Ensure every code snippet has a clear explanation of *why* it's doing what it's doing, not just a rote description of the syntax.
4.  **Narrative Flow:** Ensure the transitions between expanded sections maintain the article's overall narrative thread (the "journey").

If I have provided a specific hint, prioritize that area. Otherwise, use your expertise to identify which parts of the draft are too thin and need this deeper work.
`

func Expand() *mcp.Prompt {
	return &mcp.Prompt{
		Name:        "expand",
		Description: "Expands a working outline or draft into a more detailed article.",
		Arguments: []*mcp.PromptArgument{
			{
				Name:        "hint",
				Description: "An optional hint to guide the expansion.",
			},
		},
	}
}

func ExpandHandler(ctx context.Context, req *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
	prompt := expandPrompt
	if hint, ok := req.Params.Arguments["hint"]; ok && hint != "" {
		prompt += fmt.Sprintf("\n\n**Focus Hint:** %s", hint)
	}

	return &mcp.GetPromptResult{
		Messages: []*mcp.PromptMessage{
			{
				Role: "user",
				Content: &mcp.TextContent{
					Text: prompt,
				},
			},
		},
	}, nil
}
