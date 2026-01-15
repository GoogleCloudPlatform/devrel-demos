package symbol

import (
	"context"
	"fmt"
	"path"
	"strings"

	"github.com/danicat/godoctor/internal/tools/symbol/inspect"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the symbol resource with the server.
func Register(server *mcp.Server) {
	server.AddResourceTemplate(&mcp.ResourceTemplate{
		URITemplate: "symbol://{path}",
		Name:        "Symbol Description",
		Title:       "🔍 Go Symbol Deep-Dive",
		Description: "Detailed source and documentation for a specific Go symbol (e.g. symbol://net/http.Client or symbol:///path/to/file.go/User)",
		MIMEType:    "text/markdown",
	}, ResourceHandler)
}

// ResourceHandler handles symbol:// requests.
func ResourceHandler(ctx context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
	uri := req.Params.URI
	if !strings.HasPrefix(uri, "symbol://") {
		return nil, fmt.Errorf("invalid URI scheme")
	}
	fullPath := strings.TrimPrefix(uri, "symbol://")

	// Split into base (package or file) and symbol name
	// We assume the last element is the symbol name
	base, symName := path.Split(fullPath)
	base = strings.TrimSuffix(base, "/") // Remove trailing slash

	// Fallback: Try splitting by dot if path split didn't give a clear separation
	// This supports symbol://fmt.Println or symbol://net/http.Client
	if (base == "" || symName == "") || strings.Contains(symName, ".") {
		lastDot := strings.LastIndex(fullPath, ".")
		if lastDot != -1 {
			base = fullPath[:lastDot]
			symName = fullPath[lastDot+1:]
		}
	}

	if base == "" || symName == "" {
		return nil, fmt.Errorf("invalid symbol path: %s", fullPath)
	}

	var pkgName, fileName string
	if strings.HasSuffix(base, ".go") {
		fileName = base
	} else {
		pkgName = base
	}

	desc, err := inspect.Describe(ctx, pkgName, symName, fileName)
	if err != nil {
		return nil, err
	}

	return &mcp.ReadResourceResult{
		Contents: []*mcp.ResourceContents{
			{
				URI:      uri,
				MIMEType: "text/markdown",
				Text:     desc,
			},
		},
	}, nil
}
