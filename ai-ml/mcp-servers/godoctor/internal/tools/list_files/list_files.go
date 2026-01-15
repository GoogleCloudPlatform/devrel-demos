package list_files

import (
	"context"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["list_files"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	Path      string `json:"path" jsonschema:"The root path to list (default: .)"`
	Recursive bool   `json:"recursive,omitempty" jsonschema:"Whether to list recursively (default: true)"`
	Depth     int    `json:"depth,omitempty" jsonschema:"Maximum recursion depth (0 for no limit, default: 5 to prevent overload)"`
}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	root := args.Path
	if root == "" {
		root = "."
	}

	// Default recursive to true
	if !args.Recursive {
		// If explicitly false, we handle it by depth=1 logic basically
	} else {
		// recursive is true or omitted
	}

	maxDepth := args.Depth
	if maxDepth == 0 {
		maxDepth = 5
	}
	if !args.Recursive {
		maxDepth = 1
	}

	absRoot, err := filepath.Abs(root)
	if err != nil {
		return errorResult(fmt.Sprintf("invalid path: %v", err)), nil, nil
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Listing files in %s (Depth: %d)\n\n", absRoot, maxDepth))

	fileCount := 0
	dirCount := 0
	limitReached := false
	const maxFiles = 1000

	err = filepath.WalkDir(absRoot, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil // Skip access errors
		}

		relPath, _ := filepath.Rel(absRoot, path)
		if relPath == "." {
			return nil
		}

		// Depth check
		depth := strings.Count(relPath, string(os.PathSeparator)) + 1
		if depth > maxDepth {
			if d.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}

		// Ignore basic stuff
		if d.IsDir() && (d.Name() == ".git" || d.Name() == ".idea" || d.Name() == ".vscode" || d.Name() == "node_modules") {
			return filepath.SkipDir
		}

		if fileCount >= maxFiles {
			limitReached = true
			return filepath.SkipAll
		}

		if d.IsDir() {
			sb.WriteString(fmt.Sprintf("%s/\n", relPath))
			dirCount++
		} else {
			sb.WriteString(fmt.Sprintf("%s\n", relPath))
			fileCount++
		}

		return nil
	})

	if err != nil {
		sb.WriteString(fmt.Sprintf("\nError walking: %v\n", err))
	}

	if limitReached {
		sb.WriteString(fmt.Sprintf("\n(Limit of %d files reached, output truncated)\n", maxFiles))
	} else {
		sb.WriteString(fmt.Sprintf("\nFound %d files, %d directories.\n", fileCount, dirCount))
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: sb.String()},
		},
	}, nil, nil
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}
