package graph_test

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/danicat/godoctor/internal/graph"
)

func TestWatcher_Integration(t *testing.T) {
	// 1. Create Temp Dir
	tmpDir, err := os.MkdirTemp("", "watcher_test")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// 2. Initialize Manager
	// Create go.mod
	if err := os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module example.com/test\n\ngo 1.23\n"), 0644); err != nil {
		t.Fatal(err)
	}

	m := graph.NewManager()

	// Note: We need to ensure we don't start the global one, but our local one.
	// Initialize calls crawl and NewWatcher.
	m.Initialize(tmpDir)

	// 3. Write Initial File
	mainGo := filepath.Join(tmpDir, "main.go")
	initialContent := `package main

func Hello() {}
`
	if err := os.WriteFile(mainGo, []byte(initialContent), 0644); err != nil {
		t.Fatal(err)
	}

	// Wait for initial crawl
	// crawl is async, watcher is async.
	// we need to poll until we see the package.
	poll(t, m, "main", func(pkgName string) bool {
		// We assume package path defaults to something usable or we iterate
		pkgs := m.ListPackages()
		for _, p := range pkgs {
			if p.Name == "main" {
				obj := m.FindObject(p, "Hello")
				return obj != nil
			}
		}
		return false
	})

	// 4. Modify File (Add Function)
	newContent := `package main

func Hello() {}

func World() {}
`
	if err := os.WriteFile(mainGo, []byte(newContent), 0644); err != nil {
		t.Fatal(err)
	}

	// 5. Verify Update
	// Watcher has 500ms debounce.
	poll(t, m, "World", func(symbol string) bool {
		pkgs := m.ListPackages()
		for _, p := range pkgs {
			if p.Name == "main" {
				obj := m.FindObject(p, symbol)
				return obj != nil
			}
		}
		return false
	})
}

func poll(t *testing.T, m *graph.Manager, target string, check func(string) bool) {
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		if check(target) {
			return
		}
		time.Sleep(100 * time.Millisecond)
	}
	t.Fatalf("timeout waiting for %s", target)
}
