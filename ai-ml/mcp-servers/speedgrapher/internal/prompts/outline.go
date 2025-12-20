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

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const outlinePrompt = `Act as an expert technical writer. Please generate a structured outline for the work-in-progress article currently in your context.

The outline should contain a title, section titles, and bullet points covering all topics in each section.
- **Depth:** Ensure main sections have at least two levels of depth (sub-bullets) where necessary to fully flesh out the ideas.
- **Clarity:** The bullet points should be concise, precise, and direct.
- **Voice:** Do not worry about the author's voice at this stage; focus purely on structure and logical flow.

Please analyze the provided text and generate the outline.
`

func Outline() *mcp.Prompt {
	return &mcp.Prompt{
		Name:        "outline",
		Description: "Generates a structured outline of the current draft, concept or interview report.",
	}
}

func OutlineHandler(ctx context.Context, req *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
	return &mcp.GetPromptResult{
		Messages: []*mcp.PromptMessage{
			{
				Role: "user",
				Content: &mcp.TextContent{
					Text: outlinePrompt,
				},
			},
		},
	}, nil
}
