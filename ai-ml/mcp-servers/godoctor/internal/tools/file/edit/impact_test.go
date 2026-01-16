package edit

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/danicat/godoctor/internal/graph"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestEdit_ImpactAnalysis(t *testing.T) {
	// 1. Setup multi-package workspace
	tmpDir, err := os.MkdirTemp("", "impact-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// go.mod
	//nolint:gosec // G306: Test permissions.
	os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module example.com/impact\n\ngo 1.24\n"), 0644)

	// pkg/a/a.go
	aDir := filepath.Join(tmpDir, "pkg", "a")
	//nolint:gosec // G301: Test permissions.
	os.MkdirAll(aDir, 0755)
	aFile := filepath.Join(aDir, "a.go")
	//nolint:gosec // G306: Test permissions.
	os.WriteFile(aFile, []byte("package a\n\nfunc Hello() {}\n"), 0644)

	// pkg/b/b.go (Depends on A)
	bDir := filepath.Join(tmpDir, "pkg", "b")
	//nolint:gosec // G301: Test permissions.
	os.MkdirAll(bDir, 0755)
	bFile := filepath.Join(bDir, "b.go")
	//nolint:gosec // G306: Test permissions.
	os.WriteFile(bFile, []byte("package b\n\nimport \"example.com/impact/pkg/a\"\n\nfunc Use() {\n\ta.Hello()\n}\n"), 0644)

	// 2. Initialize Graph
	// We reset Global for test isolation (though it's a singleton, so be careful running parallel tests)
	graph.Global = graph.NewManager()
	graph.Global.Initialize(tmpDir)

	// Poll until packages are loaded
	// We need 'example.com/impact/pkg/b' to be loaded to know it imports 'a'
	deadline := time.Now().Add(10 * time.Second)
	loaded := false
	for time.Now().Before(deadline) {
		pkgs := graph.Global.ListPackages()
		count := 0
		for _, p := range pkgs {
			if strings.Contains(p.PkgPath, "example.com/impact/pkg") {
				count++
			}
		}
		if count >= 2 {
			loaded = true
			break
		}
		time.Sleep(100 * time.Millisecond)
	}
	if !loaded {
		t.Fatal("Timeout waiting for packages to load")
	}

	// 3. Perform Breaking Edit on A
	// Change Hello() to Hello(name string)
	res, _, err := toolHandler(context.TODO(), nil, Params{
		File:          aFile,
		SearchContext: "func Hello() {}",
		Replacement:   "func Hello(name string) {}",
	})
	if err != nil {
		t.Fatalf("toolHandler failed: %v", err)
	}

	output := res.Content[0].(*mcp.TextContent).Text
	// t.Logf("Tool Output:\n%s", output)

	// 4. Verify Impact Warning
	if !strings.Contains(output, "IMPACT WARNING") {
		t.Error("Expected IMPACT WARNING in output")
	}
	if !strings.Contains(output, "example.com/impact/pkg/b") {
		t.Error("Expected warning to mention dependent package 'pkg/b'")
	}
	if !strings.Contains(output, "not enough arguments") && !strings.Contains(output, "too few arguments") {
		// Go compiler error message for missing args
		t.Error("Expected compiler error details (not enough arguments)")
	}
}