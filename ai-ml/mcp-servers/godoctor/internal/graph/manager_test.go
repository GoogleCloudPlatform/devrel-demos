package graph_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/danicat/godoctor/internal/graph"
)

func setupTestGraph(t *testing.T) (string, string, string) {
	// Create a temp workspace with two packages: 'lib' and 'main'
	tmpDir := t.TempDir()

	// go.mod
	//nolint:gosec // G306: Test permissions.
	err := os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module example.com/testproject\n\ngo 1.24\n"), 0644)
	if err != nil {
		t.Fatal(err)
	}

	// lib/lib.go
	libDir := filepath.Join(tmpDir, "lib")
	//nolint:gosec // G301: Test permissions.
	if err := os.Mkdir(libDir, 0755); err != nil {
		t.Fatal(err)
	}
	libContent := `package lib

type User struct {
	Name string
}

func NewUser(name string) *User {
	return &User{Name: name}
}

func (u *User) Greet() string {
	return "Hello " + u.Name
}
`
	//nolint:gosec // G306: Test permissions.
	if err := os.WriteFile(filepath.Join(libDir, "lib.go"), []byte(libContent), 0644); err != nil {
		t.Fatal(err)
	}

	// main.go
	mainContent := `package main

import (
	"fmt"
	"example.com/testproject/lib"
)

func main() {
	u := lib.NewUser("Alice")
	fmt.Println(u.Greet())
}
`
	mainPath := filepath.Join(tmpDir, "main.go")
	//nolint:gosec // G306: Test permissions.
	if err := os.WriteFile(mainPath, []byte(mainContent), 0644); err != nil {
		t.Fatal(err)
	}

	return tmpDir, libDir, mainPath
}

func TestManager_LoadAndGet(t *testing.T) {
	tmpDir, _, mainPath := setupTestGraph(t)

	m := graph.NewManager()
	m.Initialize(tmpDir)

	// Test Load by File
	pkg, err := m.Load(mainPath)
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}
	if pkg.Name != "main" {
		t.Errorf("Expected package main, got %s", pkg.Name)
	}

	// Test Get by ID
	cachedPkg := m.Get(pkg.PkgPath)
	if cachedPkg == nil {
		t.Error("Get returned nil for loaded package")
	}
	if cachedPkg != pkg {
		t.Error("Get returned different instance than Load")
	}

	// Test ListPackages
	allPkgs := m.ListPackages()
	if len(allPkgs) < 2 { // main + lib (fmt is external/stdlib, maybe not in list if filter applies? Manager stores all loaded)
		t.Errorf("ListPackages returned too few packages: %d", len(allPkgs))
	}
}

func TestManager_FindObjectAndLocation(t *testing.T) {
	tmpDir, libDir, _ := setupTestGraph(t)
	m := graph.NewManager()
	m.Initialize(tmpDir)

	libPkg, err := m.Load(libDir)
	if err != nil {
		t.Fatalf("Failed to load lib: %v", err)
	}

	tests := []struct {
		symbol string
		want   bool
	}{
		{"NewUser", true},
		{"User", true},
		{"User.Greet", true},
		{"NonExistent", false},
	}

	for _, tt := range tests {
		obj := m.FindObject(libPkg, tt.symbol)
		if (obj != nil) != tt.want {
			t.Errorf("FindObject(%q) = %v, want %v", tt.symbol, obj, tt.want)
		}
		if obj != nil {
			src, file, line := m.FindSymbolLocation(libPkg, obj)
			if src == "" || file == "" || line == 0 {
				t.Errorf("FindSymbolLocation(%q) returned empty results", tt.symbol)
			}
		}
	}
}

func TestManager_FindReferences(t *testing.T) {
	tmpDir, libDir, mainPath := setupTestGraph(t)
	m := graph.NewManager()
	m.Initialize(tmpDir)

	// Load everything
	_, _ = m.Load(mainPath)
	libPkg, _ := m.Load(libDir)

	newUserObj := m.FindObject(libPkg, "NewUser")
	if newUserObj == nil {
		t.Fatal("Could not find NewUser object")
	}

	refs := m.FindReferences(newUserObj)
	if len(refs) == 0 {
		t.Fatal("FindReferences found 0 refs, expected at least 1 in main.go")
	}

	foundMain := false
	for _, ref := range refs {
		if strings.HasSuffix(ref.File, "main.go") {
			foundMain = true
			break
		}
	}
	if !foundMain {
		t.Error("FindReferences did not find usage in main.go")
	}
}

func TestManager_FindRelatedSymbols(t *testing.T) {
	tmpDir, libDir, _ := setupTestGraph(t)
	m := graph.NewManager()
	m.Initialize(tmpDir)

	libPkg, _ := m.Load(libDir)
	newUserObj := m.FindObject(libPkg, "NewUser") // func NewUser(...) *User

	related := m.FindRelatedSymbols(newUserObj)

	foundUser := false
	for _, obj := range related {
		if obj.Name() == "User" {
			foundUser = true
			break
		}
	}
	if !foundUser {
		t.Errorf("FindRelatedSymbols(NewUser) missed 'User'. Got: %v", related)
	}
}

// Ensure proper handling of method signatures in FindObject
func TestFindObject_Methods(t *testing.T) {
	tmpDir, libDir, _ := setupTestGraph(t)
	m := graph.NewManager()
	m.Initialize(tmpDir)

	libPkg, err := m.Load(libDir)
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}

	// Direct method lookup
	obj := m.FindObject(libPkg, "User.Greet")
	if obj == nil {
		t.Fatal("FindObject failed to find method User.Greet")
	}

	if !strings.Contains(obj.String(), "func") {
		t.Errorf("Expected func object, got %s", obj.String())
	}
}
