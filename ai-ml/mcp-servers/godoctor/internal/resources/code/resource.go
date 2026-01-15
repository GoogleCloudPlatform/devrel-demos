package code

import (
	"context"
	"fmt"
	"strings"

	"github.com/danicat/godoctor/internal/tools/file/outline"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the code resource with the server.
func Register(server *mcp.Server) {
	server.AddResourceTemplate(&mcp.ResourceTemplate{
		URITemplate: "code://{path}",
		Name:        "Code Skeleton",
		Title:       "🦴 Go Code Skeleton",
		Description: "Skeleton view (signatures only) of a Go source file (e.g. code:///path/to/main.go)",
		MIMEType:    "text/x-go",
	}, ResourceHandler)
}

// ResourceHandler handles code:// requests.
func ResourceHandler(ctx context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
	uri := req.Params.URI
	if !strings.HasPrefix(uri, "code://") {
		return nil, fmt.Errorf("invalid URI scheme")
	}
	path := strings.TrimPrefix(uri, "code://")

	skeleton, _, _, err := outline.GetOutline(path)
	if err != nil {
		return nil, fmt.Errorf("failed to get outline: %w", err)
	}

	return &mcp.ReadResourceResult{
		Contents: []*mcp.ResourceContents{
			{
				URI:      uri,
				MIMEType: "text/x-go",
				Text:     skeleton,
			},
		},
	}, nil
}
