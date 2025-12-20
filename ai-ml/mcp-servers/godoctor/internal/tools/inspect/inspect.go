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

// Package inspect implements the file inspection tool.
package inspect

import (
	"context"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"path"
	"strings"

	"github.com/danicat/godoctor/internal/resources/godoc"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the inspect_file tool with the server.
func Register(server *mcp.Server) {
	mcp.AddTool(server, &mcp.Tool{
		Name:        "inspect_file",
		Title:       "Inspect Go File",
		Description: "Reads a Go file, finds external symbol usages, and registers them as documentation resources.",
	}, NewToolHandler(server))
}

// Params defines the input parameters for the inspect_file tool.
type Params struct {
	FilePath string `json:"file_path"`
}

// NewToolHandler creates a handler with access to the server instance.
func NewToolHandler(server *mcp.Server) func(context.Context, *mcp.CallToolRequest, Params) (*mcp.CallToolResult, any, error) {
	return func(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
		if args.FilePath == "" {
			return &mcp.CallToolResult{
				IsError: true,
				Content: []mcp.Content{
					&mcp.TextContent{Text: "file_path cannot be empty"},
				},
			}, nil, nil
		}

		fset := token.NewFileSet()
		file, err := parser.ParseFile(fset, args.FilePath, nil, parser.ParseComments)
		if err != nil {
			return &mcp.CallToolResult{
				IsError: true,
				Content: []mcp.Content{
					&mcp.TextContent{Text: fmt.Sprintf("failed to parse file: %v", err)},
				},
			}, nil, nil
		}

		                // Map import names to paths
		                imports := make(map[string]string)
		                for _, imp := range file.Imports {
		                    if imp.Path == nil {
		                        continue
		                    }
		                    impPath := strings.Trim(imp.Path.Value, "\"")
		                    var name string
		                    if imp.Name != nil {
		                        name = imp.Name.Name
		                    } else {
		                        // Default name is the last element of the path
		                        // This is a heuristic; technically we should check the package name declared in that dir,
		                        // but that requires reading those files. This is good enough for 99% of cases.
		                        _, name = path.Split(impPath)
		                    }
		                    
		                    // Skip dot imports for now
		                    if name == "." {
		                        continue
		                    }
		                    if name == "_" {
		                        continue
		                    }
		                    imports[name] = impPath
		                }
		        
		                resources := make(map[string]string) // URI -> Description
		        
		                // Helper to add resource
		                addResource := func(pkgPath, symName string) {
		                    uri := fmt.Sprintf("godoc://%s", pkgPath)
		                    name := fmt.Sprintf("Package %s", pkgPath)
		                    if symName != "" {
		                        uri += "/" + symName
		                        name = fmt.Sprintf("%s.%s", pkgPath, symName)
		                    }
		                    resources[uri] = name
		                }
		        
		                // Find usages
		                ast.Inspect(file, func(n ast.Node) bool {
		                    if sel, ok := n.(*ast.SelectorExpr); ok {
		                        if id, ok := sel.X.(*ast.Ident); ok {
		                            if pkgPath, ok := imports[id.Name]; ok {
		                                addResource(pkgPath, sel.Sel.Name)
		                            }
		                        }
		                    }
		                    return true
		                })
		// Register resources
		var registered []string
		for uri, name := range resources {
			// server.AddResource is safe to call? Assuming yes.
			// We reuse the existing godoc.ResourceHandler
			server.AddResource(&mcp.Resource{
				URI:         uri,
				Name:        name,
				Description: fmt.Sprintf("Documentation for %s", name),
				MIMEType:    "text/markdown",
			}, godoc.ResourceHandler)
			registered = append(registered, name)
		}

		return &mcp.CallToolResult{
			Content: []mcp.Content{
				&mcp.TextContent{Text: fmt.Sprintf("Registered %d resources:\n- %s", len(registered), strings.Join(registered, "\n- "))},
			},
		}, nil, nil
	}
}
