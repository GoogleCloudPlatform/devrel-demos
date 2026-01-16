package server_test

import (
	"context"
	"os"
	"strings"
	"testing"

	"github.com/danicat/godoctor/internal/tools/symbol/inspect"
	"github.com/danicat/godoctor/internal/tools/file/list"
	docs "github.com/danicat/godoctor/internal/tools/go/docs"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// TestRefinedTools covers the refinements made in Phase 4.5
func TestRefinedTools(t *testing.T) {
	ctx := context.Background()
	wd, _ := os.Getwd()

	// 1. read_docs: JSON vs Markdown
	t.Run("read_docs_formats", func(t *testing.T) {
		// Happy Path: Markdown (Default)
		res, _, err := docs.Handler(ctx, nil, docs.Params{
			PackagePath: "fmt",
			SymbolName:  "Println",
		})
		if err != nil {
			t.Fatal(err)
		}
		if !strings.Contains(res.Content[0].(*mcp.TextContent).Text, "func Println") {
			t.Error("Expected markdown to contain function signature")
		}

		// Happy Path: JSON
		resJSON, _, err := docs.Handler(ctx, nil, docs.Params{
			PackagePath: "fmt",
			SymbolName:  "Println",
			Format:      "json",
		})
		if err != nil {
			t.Fatal(err)
		}
		if !strings.HasPrefix(strings.TrimSpace(resJSON.Content[0].(*mcp.TextContent).Text), "{") {
			t.Error("Expected JSON object")
		}

		// Sad Path: Invalid Format
		resErr, _, _ := docs.Handler(ctx, nil, docs.Params{
			PackagePath: "fmt",
			Format:      "yaml",
		})
		if !resErr.IsError {
			t.Error("Expected error for invalid format")
		}
	})

	// 2. list_files: Depth & Patterns
	t.Run("list_files_depth", func(t *testing.T) {
		// Happy Path: Depth 1
		res, _, err := list.Handler(ctx, nil, list.Params{
			Path:      wd,
			Recursive: true,
			Depth:     1,
		})
		if err != nil {
			t.Fatal(err)
		}
		text := res.Content[0].(*mcp.TextContent).Text
		// Check that a deep file is NOT present. e.g. internal/tools/list_files/list_files.go (depth 3)
		if strings.Contains(text, "internal/tools/list_files/list_files.go") {
			t.Error("Listed file deeper than depth 1")
		}
		// Check immediate child
		// Test running in internal/server package dir
		if !strings.Contains(text, "server.go") {
			t.Errorf("Missing server.go file. Output was:\n%s", text)
		}
	})

	// 3. inspect_symbol: Edge Cases
	t.Run("inspect_symbol_edge_cases", func(t *testing.T) {
		// Sad Path: Missing args
		res, _, _ := inspect.Handler(ctx, nil, inspect.Params{})
		if !res.IsError {
			t.Error("Expected error for missing args")
		}

		// Edge Case: Non-existent symbol
		res, _, _ = inspect.Handler(ctx, nil, inspect.Params{
			Package: "fmt",
			Symbol:  "Supercalifragilistic",
		})
		if !res.IsError {
			t.Error("Expected error for non-existent symbol")
		}
	})
}
