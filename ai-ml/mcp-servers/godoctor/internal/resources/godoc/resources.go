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

// Package godoc implements the godoc resource handler.
package godoc

import (
	"context"
	"fmt"
	"path"
	"strings"

	"github.com/danicat/godoctor/internal/godoc"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the godoc resources with the server.
func Register(server *mcp.Server) {
	server.AddResourceTemplate(&mcp.ResourceTemplate{
		URITemplate: "godoc://{path}",
		Name:        "Go Documentation",
		Description: "Documentation for Go packages and symbols (e.g. godoc://net/http or godoc://net/http/Client)",
		MIMEType:    "text/markdown",
	}, ResourceHandler)
}

// ResourceHandler handles the godoc:// resource requests.
func ResourceHandler(ctx context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
	uri := req.Params.URI
	if !strings.HasPrefix(uri, "godoc://") {
		return nil, fmt.Errorf("invalid URI scheme")
	}
	pkgPath := strings.TrimPrefix(uri, "godoc://")

	// Try as package
	doc, err := godoc.GetDocumentation(ctx, pkgPath, "")
	if err == nil {
		return &mcp.ReadResourceResult{
			Contents: []*mcp.ResourceContents{
				{
					URI:      uri,
					MIMEType: "text/markdown",
					Text:     doc,
				},
			},
		}, nil
	}

	// Try splitting for symbol (e.g. net/http/Client -> pkg: net/http, sym: Client)
	dir, file := path.Split(pkgPath)
	dir = strings.TrimSuffix(dir, "/")

	if dir != "" && file != "" {
		doc, err2 := godoc.GetDocumentation(ctx, dir, file)
		if err2 == nil {
			return &mcp.ReadResourceResult{
				Contents: []*mcp.ResourceContents{
					{
						URI:      uri,
						MIMEType: "text/markdown",
						Text:     doc,
					},
				},
			}, nil
		}
	}

	return nil, mcp.ResourceNotFoundError(uri)
}
