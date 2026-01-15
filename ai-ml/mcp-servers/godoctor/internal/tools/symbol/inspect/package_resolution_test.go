package inspect

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/danicat/godoctor/internal/graph"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestDescribe_LocalUnexported_ByPackagePath(t *testing.T) {
	// 1. Setup a temp module
	tmpDir, err := os.MkdirTemp("", "describe-repro-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Create go.mod
	modContent := "module example.com/testmod\n\ngo 1.24\n"
	if err := os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte(modContent), 0644); err != nil {
		t.Fatal(err)
	}

	// Create a subdirectory for the package
	pkgDir := filepath.Join(tmpDir, "mypkg")
	if err := os.Mkdir(pkgDir, 0755); err != nil {
		t.Fatal(err)
	}

	// Create a Go file with an unexported symbol
	srcContent := `package mypkg

type hiddenStruct struct {
	Field int
}

func secretFunc() *hiddenStruct {
	return &hiddenStruct{Field: 42}
}
`
	if err := os.WriteFile(filepath.Join(pkgDir, "secret.go"), []byte(srcContent), 0644); err != nil {
		t.Fatal(err)
	}

	// Create a Go file in root with unexported symbol
	rootSrcContent := `package testmod

func RootSecret() int { return 1 }
`
	if err := os.WriteFile(filepath.Join(tmpDir, "root.go"), []byte(rootSrcContent), 0644); err != nil {
		t.Fatal(err)
	}

	// 2. Initialize Graph with the temp dir as root
	// We need to simulate the server initialization
	graph.Global = graph.NewManager()
	graph.Global.Initialize(tmpDir)

	// 3a. Call Describe with Package path (Subpackage)
	ctx := context.Background()
	res, _, err := Handler(ctx, nil, Params{
		Package: "example.com/testmod/mypkg",
		Symbol:  "secretFunc",
	})
	if err != nil {
		t.Fatalf("toolHandler subpkg failed: %v", err)
	}
	if res.IsError {
		t.Fatalf("Handler subpkg returned error: %v", res.Content[0].(*mcp.TextContent).Text)
	}
	output := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(output, "func secretFunc()") {
		t.Errorf("Output missing source code for secretFunc. Got:\n%s", output)
	}

	// 3b. Test Root Package
	resRoot, _, err := Handler(ctx, nil, Params{
		Package: "example.com/testmod",
		Symbol:  "RootSecret",
	})
	if err != nil {
		t.Fatalf("toolHandler root failed: %v", err)
	}
	if resRoot.IsError {
		t.Fatalf("Handler root returned error: %v", resRoot.Content[0].(*mcp.TextContent).Text)
	}
	outputRoot := resRoot.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(outputRoot, "func RootSecret()") {
		t.Errorf("Output missing source code for RootSecret. Got:\n%s", outputRoot)
	}
}
