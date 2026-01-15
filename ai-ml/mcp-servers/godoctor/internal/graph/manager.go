package graph

import (
	"fmt"
	"go/ast"
	"go/printer"
	"go/types"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"golang.org/x/mod/modfile"
	"golang.org/x/tools/go/packages"
)

// PackageState holds the loaded package and metadata.
type PackageState struct {
	Pkg        *packages.Package
	LastLoaded time.Time
}

// Manager manages the graph of loaded packages (the Knowledge Graph).
type Manager struct {
	mu         sync.RWMutex
	Packages   map[string]*PackageState // Key: Import Path
	Root       string                   // Project root for indexing
	ModuleName string                   // Module name from go.mod
	watcher    *Watcher                 // File watcher
}

// Global is the singleton instance.
var Global = NewManager()

// NewManager creates a new graph manager.
func NewManager() *Manager {
	return &Manager{
		Packages: make(map[string]*PackageState),
	}
}

// Initialize sets the project root and starts background indexing.
func (m *Manager) Initialize(root string) {
	absRoot, err := filepath.Abs(root)
	if err != nil {
		absRoot = root // Fallback
	}

	m.mu.Lock()
	m.Root = absRoot
	m.mu.Unlock()

	// Try to parse go.mod to get ModuleName
	//nolint:gosec // G304: File path from internal logic/user input is expected.
	if gomod, err := os.ReadFile(filepath.Join(absRoot, "go.mod")); err == nil {
		if f, err := modfile.Parse("go.mod", gomod, nil); err == nil {
			m.mu.Lock()
			m.ModuleName = f.Module.Mod.Path
			m.mu.Unlock()
		}
	}

	// Initialize and start watcher
	w, err := NewWatcher(m)
	if err == nil {
		m.watcher = w
		if err := w.Start(absRoot); err != nil {
			fmt.Printf("Failed to start watcher: %v\n", err)
		}
	} else {
		fmt.Printf("Failed to create watcher: %v\n", err)
	}

	go m.crawl(absRoot)
}

func (m *Manager) crawl(root string) {
	// Walk the root directory and load all Go packages
	//nolint:errcheck // Best effort crawling.
	filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		//nolint:nilerr // Ignore access errors during crawl
		if err != nil || !info.IsDir() {
			return nil
		}
		// Skip hidden dirs and vendor
		name := info.Name()
		if name != "." && (strings.HasPrefix(name, ".") || name == "vendor") {
			return filepath.SkipDir
		}

		// Check if it contains Go files
		hasGo := false
		files, _ := os.ReadDir(path)
		for _, f := range files {
			if !f.IsDir() && strings.HasSuffix(f.Name(), ".go") {
				hasGo = true
				break
			}
		}

		if hasGo {
			_, _ = m.Load(path)
		}
		return nil
	})
}

// Load loads the package containing the specified file or directory.
func (m *Manager) Load(dirOrFile string) (*packages.Package, error) {
	// Check if dirOrFile is a local filesystem path
	var dir string
	var pattern string

	if _, err := os.Stat(dirOrFile); err == nil {
		// It's a local file or directory
		dir = dirOrFile
		if filepath.Ext(dir) == ".go" {
			dir = filepath.Dir(dir)
		}
		pattern = "."
	} else {
		// Assume it's an import path or pattern
		// Optimization: Check if it matches our ModuleName and resolve to local path
		m.mu.RLock()
		modName := m.ModuleName
		root := m.Root
		m.mu.RUnlock()

		if modName != "" && strings.HasPrefix(dirOrFile, modName) {
			rel := strings.TrimPrefix(dirOrFile, modName)
			// Handle case where import path is exactly module name
			if rel == "" {
				rel = "."
			}
			localPath := filepath.Join(root, rel)
			if info, err := os.Stat(localPath); err == nil && info.IsDir() {
				dir = localPath
				pattern = "."
			} else {
				// Fallback to standard behavior if not found locally
				dir = root
				if dir == "" {
					dir = "."
				}
				pattern = dirOrFile
			}
		} else {
			dir = root
			if dir == "" {
				dir = "."
			}
			pattern = dirOrFile
		}
	}

	// 2. Run packages.Load
	cfg := &packages.Config{
		Mode: packages.NeedName | packages.NeedFiles | packages.NeedCompiledGoFiles |
			packages.NeedImports | packages.NeedDeps | packages.NeedTypes |
			packages.NeedSyntax | packages.NeedTypesInfo,
		Dir: dir,
	}

	pkgs, err := packages.Load(cfg, pattern)

	// Retry with wildcard if direct load fails (Discovery Mode)
	if (err != nil || len(pkgs) == 0) && !strings.HasSuffix(pattern, "...") && !strings.HasSuffix(pattern, ".go") && !strings.HasPrefix(pattern, ".") {
		fmt.Printf("Direct load failed for %s, trying wildcard discovery...\n", pattern)
		wildcardPattern := strings.TrimSuffix(pattern, "/") + "/..."
		pkgsWild, errWild := packages.Load(cfg, wildcardPattern)
		if errWild == nil && len(pkgsWild) > 0 {
			pkgs = pkgsWild
			err = nil
		}
	}

	if err != nil {
		return nil, fmt.Errorf("packages.Load failed: %w", err)
	}
	if len(pkgs) == 0 {
		return nil, fmt.Errorf("no packages found in %s", dir)
	}

	// 3. Cache results
	m.mu.Lock()
	defer m.mu.Unlock()

	var retPkg *packages.Package

	// Helper to recursively cache
	var cacheFunc func(*packages.Package)
	cacheFunc = func(p *packages.Package) {
		if _, exists := m.Packages[p.PkgPath]; exists {
			return
		}
		m.Packages[p.PkgPath] = &PackageState{
			Pkg:        p,
			LastLoaded: time.Now(),
		}
		for _, imp := range p.Imports {
			cacheFunc(imp)
		}
	}

	for _, pkg := range pkgs {
		cacheFunc(pkg)

		// Heuristic: The package in the requested directory is likely the one we want to return.
		if retPkg == nil {
			// Return the canonical (cached) package instance to ensure type identity consistency.
			// cacheFunc has guaranteed it exists in the map.
			retPkg = m.Packages[pkg.PkgPath].Pkg
		}
	}

	return retPkg, nil
}

// Get returns a cached package by import path.
func (m *Manager) Get(pkgPath string) *packages.Package {
	m.mu.RLock()
	defer m.mu.RUnlock()
	state, ok := m.Packages[pkgPath]
	if !ok {
		return nil
	}
	return state.Pkg
}

// ListPackages returns a list of all loaded packages.
func (m *Manager) ListPackages() []*packages.Package {
	m.mu.RLock()
	defer m.mu.RUnlock()
	pkgs := make([]*packages.Package, 0, len(m.Packages))
	for _, p := range m.Packages {
		pkgs = append(pkgs, p.Pkg)
	}
	return pkgs
}

// Reference represents a usage of a symbol.
type Reference struct {
	File string
	Line int
	Col  int
}

// FindReferences finds all usages of the given object across all loaded packages.
func (m *Manager) FindReferences(target types.Object) []Reference {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var refs []Reference
	for _, state := range m.Packages {
		pkg := state.Pkg
		if pkg.TypesInfo == nil {
			continue
		}

		for ident, obj := range pkg.TypesInfo.Uses {
			if obj == target {
				pos := pkg.Fset.Position(ident.Pos())
				refs = append(refs, Reference{
					File: pos.Filename,
					Line: pos.Line,
					Col:  pos.Column,
				})
			}
		}
	}
	return refs
}

// FindImporters returns all loaded packages that import the given package path.
func (m *Manager) FindImporters(pkgPath string) []*packages.Package {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var importers []*packages.Package
	for _, state := range m.Packages {
		pkg := state.Pkg
		for _, imp := range pkg.Imports {
			if imp.PkgPath == pkgPath {
				importers = append(importers, pkg)
				break
			}
		}
	}
	return importers
}

// FindRelatedSymbols finds types used in the signature of the given object.
func (m *Manager) FindRelatedSymbols(obj types.Object) []types.Object {
	var related []types.Object
	seen := make(map[types.Object]bool)
	seen[obj] = true // Don't include self

	var collect func(t types.Type)
	collect = func(t types.Type) {
		switch t := t.(type) {
		case *types.Named:
			obj := t.Obj()
			if !seen[obj] {
				seen[obj] = true
				related = append(related, obj)
			}
			// We don't recurse into underlying types of Named types to enforce "one level deep"
		case *types.Pointer:
			collect(t.Elem())
		case *types.Slice:
			collect(t.Elem())
		case *types.Array:
			collect(t.Elem())
		case *types.Map:
			collect(t.Key())
			collect(t.Elem())
		case *types.Chan:
			collect(t.Elem())
		case *types.Struct:
			for i := 0; i < t.NumFields(); i++ {
				collect(t.Field(i).Type())
			}
		case *types.Interface:
			for i := 0; i < t.NumMethods(); i++ {
				collect(t.Method(i).Type())
			}
		case *types.Signature:
			if t.Recv() != nil {
				collect(t.Recv().Type())
			}
			// Recurse for function types (e.g. callbacks)
			for i := 0; i < t.Params().Len(); i++ {
				collect(t.Params().At(i).Type())
			}
			for i := 0; i < t.Results().Len(); i++ {
				collect(t.Results().At(i).Type())
			}
		}
	}

	if obj.Type() == nil {
		return nil
	}

	switch t := obj.Type().(type) {
	case *types.Signature:
		collect(t)
	case *types.Named:
		// If describing a type, show types of its underlying fields/elements
		collect(t.Underlying())
	case *types.Struct:
		for i := 0; i < t.NumFields(); i++ {
			collect(t.Field(i).Type())
		}
	case *types.Interface:
		for i := 0; i < t.NumMethods(); i++ {
			collect(t.Method(i).Type())
		}
	}

	return related
}

// FindObject finds a types.Object by name in a specific package.
func (m *Manager) FindObject(pkg *packages.Package, name string) types.Object {
	if pkg.Types == nil || pkg.Types.Scope() == nil {
		return nil
	}

	// 1. Direct lookup in package scope
	if obj := pkg.Types.Scope().Lookup(name); obj != nil {
		return obj
	}

	// 2. Handle Method lookup (Receiver.Method)
	if strings.Contains(name, ".") {
		parts := strings.Split(name, ".")
		if len(parts) == 2 {
			typeName, methodName := parts[0], parts[1]
			obj := pkg.Types.Scope().Lookup(typeName)
			if obj != nil {
				if t, ok := obj.Type().Underlying().(*types.Struct); ok {
					// This is simplistic, doesn't handle named types well.
					// Let's use LookupFieldOrMethod.
					_ = t
				}
				// Robust lookup for named types
				if named, ok := obj.Type().(*types.Named); ok {
					for i := 0; i < named.NumMethods(); i++ {
						m := named.Method(i)
						if m.Name() == methodName {
							return m
						}
					}
				}
			}
		}
	}

	return nil
}

// FindSymbolLocation returns the source code and location of a symbol.
func (m *Manager) FindSymbolLocation(pkg *packages.Package, obj types.Object) (string, string, int) {
	pos := pkg.Fset.Position(obj.Pos())

	// Find the AST node to extract source
	for _, file := range pkg.Syntax {
		if pkg.Fset.File(file.Pos()).Name() == pos.Filename {
			var node ast.Node
			// We search for the declaration that contains the object's position
			ast.Inspect(file, func(n ast.Node) bool {
				if n == nil {
					return false
				}

				switch x := n.(type) {
				case *ast.FuncDecl:
					if x.Name.Pos() == obj.Pos() {
						node = x
						return false
					}
				case *ast.GenDecl:
					for _, spec := range x.Specs {
						switch s := spec.(type) {
						case *ast.TypeSpec:
							if s.Name.Pos() == obj.Pos() {
								node = x
								return false
							}
						case *ast.ValueSpec:
							for _, name := range s.Names {
								if name.Pos() == obj.Pos() {
									node = x
									return false
								}
							}
						}
					}
				}
				return true
			})

			if node != nil {
				var buf strings.Builder
				//nolint:errcheck // bytes.Buffer write
				printer.Fprint(&buf, pkg.Fset, node)
				return buf.String(), pos.Filename, pos.Line
			}
		}
	}

	return "", pos.Filename, pos.Line
}

// Parent is a hacky way to find parent node during Inspect if not provided by AST.
// Better: Use a custom inspector or pre-computed parent map if needed.

