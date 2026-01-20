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

	"github.com/danicat/godoctor/internal/roots"
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
	mu          sync.RWMutex
	Packages    map[string]*PackageState // Key: Import Path
	RootModules map[string]string        // Mapping from Root to ModuleName
	watcher     *Watcher                 // File watcher
}

// Global is the singleton instance.
var Global = NewManager()

// NewManager creates a new graph manager.
func NewManager() *Manager {
	return &Manager{
		Packages:    make(map[string]*PackageState),
		RootModules: make(map[string]string),
	}
}

// Close stops the background watcher and cleans up resources.
func (m *Manager) Close() error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.watcher != nil {
		return m.watcher.Close()
	}
	return nil
}

// Initialize sets a project root and starts background indexing.
func (m *Manager) Initialize(root string) {
	absRoot, err := filepath.Abs(root)
	if err != nil {
		absRoot = root // Fallback
	}

	// Register with roots package
	roots.Global.Add(absRoot)

	// Try to parse go.mod to get ModuleName
	//nolint:gosec // G304: File path from internal logic/user input is expected.
	if gomod, err := os.ReadFile(filepath.Join(absRoot, "go.mod")); err == nil {
		if f, err := modfile.Parse("go.mod", gomod, nil); err == nil {
			m.mu.Lock()
			m.RootModules[absRoot] = f.Module.Mod.Path
			m.mu.Unlock()
		}
	}

	// Initialize and start watcher if not already started
	m.mu.Lock()
	w := m.watcher
	m.mu.Unlock()

	if w == nil {
		nw, err := NewWatcher(m)
		if err == nil {
			m.mu.Lock()
			m.watcher = nw
			m.mu.Unlock()
			w = nw
		} else {
			fmt.Fprintf(os.Stderr, "Failed to create watcher: %v\n", err)
		}
	}

	if w != nil {
		go func() {
			if err := w.Start(absRoot); err != nil {
				fmt.Fprintf(os.Stderr, "Failed to start watcher for %s: %v\n", absRoot, err)
			}
		}()
	}
}

// Scan performs a lightweight scan of all registered project roots.
func (m *Manager) Scan() error {
	rts := roots.Global.Get()

	for _, root := range rts {
		cfg := &packages.Config{
			Mode: packages.NeedName | packages.NeedFiles | packages.NeedImports,
			Dir:  root,
		}

		pkgs, err := packages.Load(cfg, "./...")
		if err != nil {
			fmt.Fprintf(os.Stderr, "Warning: scan failed for root %s: %v\n", root, err)
			continue
		}

		m.mu.Lock()
		for _, p := range pkgs {
			m.cachePackage(p)
		}
		m.mu.Unlock()
	}
	return nil
}

func (m *Manager) cachePackage(p *packages.Package) {
	// Heuristic: If package name is empty, it might be a failed load.
	// Try to infer it from PkgPath if possible.
	if p.Name == "" && p.PkgPath != "" && p.PkgPath != "command-line-arguments" {
		parts := strings.Split(p.PkgPath, "/")
		p.Name = parts[len(parts)-1]
	}

	// If existing package is "better" (has types), keep it unless p also has types (refresh)
	if existing, exists := m.Packages[p.PkgPath]; exists {
		// If we already have a loaded package with types, keep it to ensure
		// type identity consistency across the graph.
		if existing.Pkg.TypesInfo != nil {
			return
		}
		// If both are "light" (no types), we already have it, so stop recursion (fixes A->B->A loop)
		if p.TypesInfo == nil {
			return
		}
	}

	m.Packages[p.PkgPath] = &PackageState{
		Pkg:        p,
		LastLoaded: time.Now(),
	}
	for _, imp := range p.Imports {
		m.cachePackage(imp)
	}
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
		// Optimization: Check if it matches our RootModules and resolve to local path
		m.mu.RLock()
		rootMods := make(map[string]string)
		for k, v := range m.RootModules {
			rootMods[k] = v
		}
		m.mu.RUnlock()

		rts := roots.Global.Get()

		for _, root := range rts {
			modName := rootMods[root]
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
					goto Found
				}
			}
		}

		// Fallback to standard behavior if not found locally
		if dir == "" {
			if len(rts) > 0 {
				dir = rts[0]
			} else {
				dir = "."
			}
			pattern = dirOrFile
		}
	Found:
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
		fmt.Fprintf(os.Stderr, "Direct load failed for %s, trying wildcard discovery...\n", pattern)
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

	for _, pkg := range pkgs {
		m.cachePackage(pkg)

		// Heuristic: The package in the requested directory is likely the one we want to return.
		if retPkg == nil {
			// Return the canonical (cached) package instance to ensure type identity consistency.
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
