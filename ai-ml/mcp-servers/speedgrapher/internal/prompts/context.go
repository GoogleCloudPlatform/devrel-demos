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

func Context() *mcp.Prompt {
	return &mcp.Prompt{
		Name:        "context",
		Description: "Loads the current work-in-progress article to context for further commands.",
	}
}

func ContextHandler(ctx context.Context, req *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
	return &mcp.GetPromptResult{
		Messages: []*mcp.PromptMessage{
			{
				Role: "user",
				Content: &mcp.TextContent{
					Text: "Please identify and reload the current work-in-progress article into your context. If there are multiple potential files, ask me to clarify which one is the active draft. I need to ensure you have the full, most up-to-date version of the text before we proceed.",
				},
			},
		},
	}, nil
}
