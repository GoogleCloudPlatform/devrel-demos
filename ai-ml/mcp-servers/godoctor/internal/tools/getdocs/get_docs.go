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

// Package getdocs implements the documentation retrieval tool.
package getdocs

import (
	"context"
	"fmt"

	"github.com/danicat/godoctor/internal/godoc"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the get_docs tool with the server.
func Register(server *mcp.Server) {
	mcp.AddTool(server, &mcp.Tool{
		Name:  "read_godoc",
		Title: "Read Go Documentation",
		Description: "Read Go documentation for packages and symbols. " +
			"Returns definitions, comments, and examples in Markdown format. " +
			"Useful for discovering standard library functions and external package usage.",
	}, ToolHandler)
}

// Params defines the input parameters for the get_docs tool.
type Params struct {
	PackagePath string `json:"package_path"`
	SymbolName  string `json:"symbol_name,omitempty"`
}

// ToolHandler handles the get_docs tool execution.
func ToolHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.PackagePath == "" {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: "package_path cannot be empty"},
			},
		}, nil, nil
	}

	markdown, err := godoc.GetDocumentation(ctx, args.PackagePath, args.SymbolName)
	if err != nil {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: fmt.Sprintf("failed to read documentation: %v", err)},
			},
		}, nil, nil
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: markdown},
		},
	}, nil, nil
}