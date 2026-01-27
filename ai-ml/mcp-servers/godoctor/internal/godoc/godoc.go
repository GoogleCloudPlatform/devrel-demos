// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Package godoc implements the core logic for retrieving and parsing Go documentation.
package godoc

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"go/ast"
	"go/doc"
	"go/parser"
	"go/printer"
	"go/token"
	"os"
	"os/exec"
	"regexp"
	"strings"

	"golang.org/x/tools/go/packages"
)

// Load resolves an import path and returns documentation.
// It performs disk I/O ("go list") and parsing. Use this when starting from a string path.
func Load(ctx context.Context, pkgPath, symbolName string) (*Doc, error) {
	return loadInternal(ctx, pkgPath, symbolName, false)
}

// LoadWithFallback is like Load but attempts to find parent packages if the exact match fails.
func LoadWithFallback(ctx context.Context, pkgPath, symbolName string) (*Doc, error) {
	return loadInternal(ctx, pkgPath, symbolName, true)
}

func loadInternal(ctx context.Context, pkgPath, symbolName string, allowFallback bool) (*Doc, error) {
	// Try to find the package directory locally
	pkgDir, err := resolvePackageDir(ctx, pkgPath)
	if err != nil {
		// Fallback: try to fetch the package in a temp directory
		doc, fetchErr := fetchAndRetryStructured(ctx, pkgPath, symbolName, err)
		if fetchErr == nil {
			return doc, nil
		}

		if allowFallback {
			// Try walking up the path
			parts := strings.Split(pkgPath, "/")
			minParts := 1
			if strings.Contains(parts[0], ".") {
				minParts = 3
			}

			for i := len(parts) - 1; i >= minParts; i-- {
				parentPath := strings.Join(parts[:i], "/")
				if doc, err := loadInternal(ctx, parentPath, "", false); err == nil {
					doc.ResolvedPath = pkgPath
					return doc, nil
				}
			}
		}
		return nil, fetchErr
	}

	result, err := parsePackageDocs(ctx, pkgPath, pkgDir, symbolName, pkgPath)
	if err != nil {
		return nil, fmt.Errorf("failed to parse documentation: %w", err)
	}
	return result, nil
}

// Extract returns documentation from an already loaded packages.Package.
// It is efficient (no I/O) as it reuses the existing AST and Type information.
// Use this when you have a *packages.Package available.
func Extract(pkg *packages.Package, symbolName string) (*Doc, error) {
	if pkg == nil {
		return nil, errors.New("package is nil")
	}

	// Transform packages.Package files into godoc Doc
	result := &Doc{
		ImportPath:  pkg.PkgPath,
		Package:     pkg.Name,
		PkgGoDevURL: fmt.Sprintf("https://pkg.go.dev/%s", pkg.PkgPath),
	}

	// Compute documentation using the syntax already loaded in the package
	targetPkg, err := doc.NewFromFiles(pkg.Fset, pkg.Syntax, pkg.PkgPath)
	if err != nil {
		return nil, fmt.Errorf("doc.NewFromFiles failed: %w", err)
	}

	if symbolName == "" {
		result.Description = targetPkg.Doc
		result.Definition = fmt.Sprintf("package %s // import %q", pkg.Name, pkg.PkgPath)
		// Populate lists...
		for _, f := range targetPkg.Funcs {
			result.Funcs = append(result.Funcs, bufferCode(pkg.Fset, f.Decl))
		}
		for _, t := range targetPkg.Types {
			result.Types = append(result.Types, bufferCode(pkg.Fset, t.Decl))
		}
		return result, nil
	}

	result.SymbolName = symbolName
	result.PkgGoDevURL = fmt.Sprintf("https://pkg.go.dev/%s#%s", pkg.PkgPath, symbolName)

	found, _ := findSymbol(pkg.Fset, targetPkg, symbolName, result)
	if !found {
		return nil, fmt.Errorf("symbol %q not found in package %s", symbolName, pkg.PkgPath)
	}

	return result, nil
}

// GetDocumentation retrieves the documentation for a package or symbol as Markdown.
func GetDocumentation(ctx context.Context, pkgPath, symbolName string) (string, error) {
	doc, err := Load(ctx, pkgPath, symbolName)
	if err != nil {
		return "", err
	}
	return Render(doc), nil
}

// GetDocumentationWithFallback attempts to retrieve documentation for a package.
// If the specific package documentation is not found, it attempts to find documentation
// for parent paths (module roots) and returns it with a hint.
func GetDocumentationWithFallback(ctx context.Context, pkgPath string) string {
	// 1. Try exact match
	doc, err := Load(ctx, pkgPath, "")
	if err == nil && doc.Package != "" {
		return Render(doc)
	}

	// 2. Fallback: Walk up the path
	parts := strings.Split(pkgPath, "/")
	// Heuristic: For domain-based packages (github.com/...), keep at least 3 parts.
	minParts := 1
	if strings.Contains(parts[0], ".") {
		minParts = 3
	}

	for i := len(parts) - 1; i >= minParts; i-- {
		parentPath := strings.Join(parts[:i], "/")
		doc, err := Load(ctx, parentPath, "")
		if err == nil && doc.Package != "" {
			return fmt.Sprintf("> ℹ️ Could not find docs for `%s`. Showing docs for module root `%s` instead.\n\n%s", pkgPath, parentPath, Render(doc))
		}
	}

	return ""
}

// Example represents a code example extracted from documentation.
type Example struct {
	Name   string `json:"name"`
	Code   string `json:"code"`
	Output string `json:"output,omitempty"`
}

// Doc represents the parsed documentation.
type Doc struct {
	Package      string    `json:"package"`
	ImportPath   string    `json:"importPath"`
	ResolvedPath string    `json:"resolvedPath,omitempty"`
	SymbolName   string    `json:"symbolName,omitempty"`
	Type         string    `json:"type,omitempty"` // "function", "type", "var", "const"
	Definition   string    `json:"definition,omitempty"`
	Description  string    `json:"description"`
	Examples     []Example `json:"examples,omitempty"`
	SubPackages  []string  `json:"subPackages,omitempty"`
	PkgGoDevURL  string    `json:"pkgGoDevURL"`

	// Lists of symbols (signatures or summaries)
	Funcs  []string `json:"funcs,omitempty"`
	Types  []string `json:"types,omitempty"`
	Vars   []string `json:"vars,omitempty"`
	Consts []string `json:"consts,omitempty"`

	// Extra fields for Describe superset
	SourcePath string   `json:"sourcePath,omitempty"`
	Line       int      `json:"line,omitempty"`
	References []string `json:"references,omitempty"`
}

func resolvePackageDir(ctx context.Context, pkgPath string) (string, error) {
	// Use 'go list' to find the directory of the package
	cmd := exec.CommandContext(ctx, "go", "list", "-f", "{{.Dir}}", pkgPath)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("go list failed: %v", string(out))
	}
	return strings.TrimSpace(string(out)), nil
}

func parsePackageDocs(ctx context.Context, importPath, pkgDir, symbolName, requestedPath string) (*Doc, error) {
	fset := token.NewFileSet()
	pkgs, err := parser.ParseDir(fset, pkgDir, nil, parser.ParseComments)
	if err != nil {
		return nil, fmt.Errorf("parser.ParseDir failed: %w", err)
	}

	// Collect all files from all packages (e.g. "http" and "http_test")
	var files []*ast.File
	for _, pkg := range pkgs {
		for _, file := range pkg.Files {
			files = append(files, file)
		}
	}

	result := &Doc{
		ImportPath:  importPath,
		PkgGoDevURL: fmt.Sprintf("https://pkg.go.dev/%s", importPath),
	}

	if requestedPath != "" && requestedPath != importPath {
		result.ResolvedPath = requestedPath
	}

	// Always look for sub-packages
	subs := ListSubPackages(ctx, pkgDir)
	for _, sub := range subs {
		if sub != importPath { // Exclude self
			result.SubPackages = append(result.SubPackages, sub)
		}
	}

	if len(files) == 0 {
		// If no files found, but we have subpackages, return a module overview
		if len(result.SubPackages) > 0 {
			result.Package = "module_root"
			result.Description = fmt.Sprintf("Module root for %s. No Go source files found in the root directory, but sub-packages exist.", importPath)
			return result, nil
		}
		return nil, fmt.Errorf("no files found in package %s", importPath)
	}

	// Compute documentation using all files
	targetPkg, err := doc.NewFromFiles(fset, files, importPath)
	if err != nil {
		return nil, fmt.Errorf("doc.NewFromFiles failed: %w", err)
	}

	pkgName := targetPkg.Name
	if pkgName == "" {
		parts := strings.Split(importPath, "/")
		pkgName = parts[len(parts)-1]
	}
	result.Package = pkgName

	if symbolName == "" {
		result.Description = targetPkg.Doc
		result.Definition = fmt.Sprintf("package %s // import %q", pkgName, importPath)
		result.Examples = extractExamples(fset, targetPkg.Examples)

		// Populate symbol lists
		for _, f := range targetPkg.Funcs {
			result.Funcs = append(result.Funcs, bufferCode(fset, f.Decl))
		}
		for _, t := range targetPkg.Types {
			// Just the type decl, not full methods unless we want detailed summary
			result.Types = append(result.Types, bufferCode(fset, t.Decl))
		}
		for _, v := range targetPkg.Vars {
			result.Vars = append(result.Vars, bufferCode(fset, v.Decl))
		}
		for _, c := range targetPkg.Consts {
			result.Consts = append(result.Consts, bufferCode(fset, c.Decl))
		}

		return result, nil
	}

	result.SymbolName = symbolName
	result.PkgGoDevURL = fmt.Sprintf("https://pkg.go.dev/%s#%s", importPath, symbolName)

	found, candidates := findSymbol(fset, targetPkg, symbolName, result)
	if !found {
		fuzzyMatches := findFuzzyMatches(symbolName, candidates)
		msg := fmt.Sprintf("symbol %q not found in package %s", symbolName, importPath)
		if len(fuzzyMatches) > 0 {
			msg += fmt.Sprintf(". Did you mean: %s?", strings.Join(fuzzyMatches, ", "))
		}
		return nil, errors.New(msg)
	}

	return result, nil
}

func findSymbol(fset *token.FileSet, pkg *doc.Package, symName string, result *Doc) (bool, []string) {
	var candidates []string
	add := func(name string) { candidates = append(candidates, name) }

	if checkFuncs(fset, pkg, symName, result, add) {
		return true, nil
	}
	if checkTypes(fset, pkg, symName, result, add) {
		return true, nil
	}
	if checkVars(fset, pkg, symName, result, add) {
		return true, nil
	}
	if checkConsts(fset, pkg, symName, result, add) {
		return true, nil
	}

	return false, candidates
}

func checkFuncs(fset *token.FileSet, pkg *doc.Package, symName string, result *Doc, add func(string)) bool {
	for _, f := range pkg.Funcs {
		if f.Name == symName {
			populateFunc(fset, pkg, f, result)
			return true
		}
		add(f.Name)
	}
	return false
}

func checkTypes(fset *token.FileSet, pkg *doc.Package, symName string, result *Doc, add func(string)) bool {
	for _, t := range pkg.Types {
		if t.Name == symName {
			result.Type = "type"
			result.Definition = bufferCode(fset, t.Decl)
			result.Description = t.Doc
			result.Examples = extractExamples(fset, t.Examples)
			return true
		}
		add(t.Name)

		for _, f := range t.Funcs {
			if f.Name == symName {
				populateFunc(fset, pkg, f, result)
				return true
			}
			add(f.Name)
		}

		for _, m := range t.Methods {
			if m.Name == symName {
				result.Type = "method"
				result.Definition = bufferCode(fset, m.Decl)
				result.Description = m.Doc
				result.Examples = extractExamples(fset, m.Examples)
				return true
			}
			add(m.Name)
		}
	}
	return false
}

func checkVars(fset *token.FileSet, pkg *doc.Package, symName string, result *Doc, add func(string)) bool {
	for _, v := range pkg.Vars {
		for _, name := range v.Names {
			if name == symName {
				result.Type = "var"
				result.Definition = bufferCode(fset, v.Decl)
				result.Description = v.Doc
				return true
			}
			add(name)
		}
	}
	return false
}

func checkConsts(fset *token.FileSet, pkg *doc.Package, symName string, result *Doc, add func(string)) bool {
	for _, c := range pkg.Consts {
		for _, name := range c.Names {
			if name == symName {
				result.Type = "const"
				result.Definition = bufferCode(fset, c.Decl)
				result.Description = c.Doc
				return true
			}
			add(name)
		}
	}
	return false
}

func populateFunc(fset *token.FileSet, pkg *doc.Package, f *doc.Func, result *Doc) {
	result.Type = "function"
	result.Definition = bufferCode(fset, f.Decl)

	if typeDef := findReturnTypeDefinition(fset, pkg, f); typeDef != "" {
		result.Definition += "\n\n" + typeDef
	}

	result.Description = f.Doc
	result.Examples = extractExamples(fset, f.Examples)
}

func findReturnTypeDefinition(fset *token.FileSet, pkg *doc.Package, f *doc.Func) string {
	if f.Decl.Type.Results == nil || len(f.Decl.Type.Results.List) == 0 {
		return ""
	}

	// Get the first return value type
	retType := f.Decl.Type.Results.List[0].Type

	var typeName string

	// Handle pointers (*Type) or values (Type)
	switch t := retType.(type) {
	case *ast.StarExpr:
		if ident, ok := t.X.(*ast.Ident); ok {
			typeName = ident.Name
		}
	case *ast.Ident:
		typeName = t.Name
	}

	if typeName == "" {
		return ""
	}

	// Search for this type in the package
	for _, t := range pkg.Types {
		if t.Name == typeName {
			return bufferCode(fset, t.Decl)
		}
	}

	return ""
}

func extractExamples(fset *token.FileSet, examples []*doc.Example) []Example {
	result := make([]Example, 0, len(examples))
	for _, ex := range examples {
		code := bufferCode(fset, ex.Code)
		result = append(result, Example{
			Name:   ex.Name,
			Code:   code,
			Output: ex.Output,
		})
	}
	return result
}

func bufferCode(fset *token.FileSet, node any) string {
	var buf bytes.Buffer
	if err := printer.Fprint(&buf, fset, node); err != nil {
		return fmt.Sprintf("error printing code: %v", err)
	}
	return buf.String()
}

// Render converts a Doc to Markdown.
func Render(doc *Doc) string {
	var buf strings.Builder

	buf.WriteString(fmt.Sprintf("# %s\n\n", doc.ImportPath))

	if doc.ResolvedPath != "" {
		if strings.HasPrefix(doc.ResolvedPath, doc.ImportPath) {
			buf.WriteString(fmt.Sprintf("> ℹ️ **Note:** Could not find `%s`. Showing documentation for parent module `%s` instead.\n\n", doc.ResolvedPath, doc.ImportPath))
		} else {
			buf.WriteString(fmt.Sprintf("> **Note:** Redirected from %s\n\n", doc.ResolvedPath))
		}
	}

	if doc.SymbolName != "" {
		buf.WriteString(fmt.Sprintf("## %s %s\n\n", doc.Type, doc.SymbolName))
	}

	if doc.SourcePath != "" {
		buf.WriteString(fmt.Sprintf("Defined in: `%s:%d`\n\n", doc.SourcePath, doc.Line))
	}

	if doc.Definition != "" {
		buf.WriteString("```go\n")
		buf.WriteString(doc.Definition)
		buf.WriteString("\n```\n\n")
	}

	buf.WriteString(doc.Description)
	buf.WriteString("\n\n")

	if len(doc.Examples) > 0 {
		buf.WriteString("### Examples\n\n")
		for _, ex := range doc.Examples {
			name := ex.Name
			if name == "" {
				name = "Package Example"
			}
			buf.WriteString(fmt.Sprintf("#### %s\n\n", name))
			buf.WriteString("```go\n")
			buf.WriteString(ex.Code)
			buf.WriteString("\n```\n")
			if ex.Output != "" {
				buf.WriteString("\n**Output:**\n```\n")
				buf.WriteString(ex.Output)
				buf.WriteString("\n```\n")
			}
			buf.WriteString("\n")
		}
	}

	// Render Symbol Lists (if available and not focusing on a single symbol)
	if doc.SymbolName == "" {
		if len(doc.Consts) > 0 {
			buf.WriteString("### Constants\n\n")
			buf.WriteString("```go\n")
			for _, c := range doc.Consts {
				buf.WriteString(c)
				buf.WriteString("\n")
			}
			buf.WriteString("```\n\n")
		}
		if len(doc.Vars) > 0 {
			buf.WriteString("### Variables\n\n")
			buf.WriteString("```go\n")
			for _, v := range doc.Vars {
				buf.WriteString(v)
				buf.WriteString("\n")
			}
			buf.WriteString("```\n\n")
		}
		if len(doc.Funcs) > 0 {
			buf.WriteString("### Functions\n\n")
			buf.WriteString("```go\n")
			for _, f := range doc.Funcs {
				buf.WriteString(f)
				buf.WriteString("\n\n")
			}
			buf.WriteString("```\n\n")
		}
		if len(doc.Types) > 0 {
			buf.WriteString("### Types\n\n")
			buf.WriteString("```go\n")
			for _, t := range doc.Types {
				buf.WriteString(t)
				buf.WriteString("\n\n")
			}
			buf.WriteString("```\n\n")
		}
	}

	if len(doc.References) > 0 {
		buf.WriteString("### Usages\n\n")
		for _, ref := range doc.References {
			buf.WriteString(fmt.Sprintf("- %s\n", ref))
		}
		buf.WriteString("\n")
	}

	if len(doc.SubPackages) > 0 {
		buf.WriteString("### Sub-packages\n\n")
		for _, sub := range doc.SubPackages {
			buf.WriteString(fmt.Sprintf("- %s\n", sub))
		}
		buf.WriteString("\n")
	}

	buf.WriteString(fmt.Sprintf("[View on pkg.go.dev](%s)\n", doc.PkgGoDevURL))
	return buf.String()
}

func findFuzzyMatches(query string, candidates []string) []string {
	var matches []string
	lowerQuery := strings.ToLower(query)

	for _, c := range candidates {
		// Case insensitive match
		if strings.EqualFold(query, c) {
			matches = append(matches, c)
			continue
		}

		// Levenshtein distance < 3 (allow small typos)
		dist := levenshtein(lowerQuery, strings.ToLower(c))
		if dist <= 2 {
			matches = append(matches, c)
		}
	}
	// Limit to top 5
	if len(matches) > 5 {
		return matches[:5]
	}
	return matches
}

func levenshtein(s1, s2 string) int {
	r1, r2 := []rune(s1), []rune(s2)
	n, m := len(r1), len(r2)
	if n > m {
		r1, r2 = r2, r1
		n, m = m, n
	}

	currentRow := make([]int, n+1)
	for i := 0; i <= n; i++ {
		currentRow[i] = i
	}

	for i := 1; i <= m; i++ {
		previousRow := currentRow
		currentRow = make([]int, n+1)
		currentRow[0] = i
		for j := 1; j <= n; j++ {
			add, del, change := previousRow[j]+1, currentRow[j-1]+1, previousRow[j-1]
			if r1[j-1] != r2[i-1] {
				change++
			}

			minVal := add
			if del < minVal {
				minVal = del
			}
			if change < minVal {
				minVal = change
			}
			currentRow[j] = minVal
		}
	}
	return currentRow[n]
}

func fetchAndRetryStructured(ctx context.Context, pkgPath, symbolName string, originalErr error) (*Doc, error) {
	tempDir, err := setupTempModule(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to setup temp module: %w", err)
	}
	defer func() {
		_ = os.RemoveAll(tempDir)
	}()

	pkgDir, actualPkgPath, err := downloadPackage(ctx, tempDir, pkgPath)
	if err != nil {
		// Attempt to provide suggestions from standard library and local context
		suggestions := suggestPackages(ctx, pkgPath)

		if len(suggestions) > 0 {
			return nil, fmt.Errorf("package %q not found. Did you mean: %s?", pkgPath, strings.Join(suggestions, ", "))
		}

		return nil, fmt.Errorf("failed to download package %q: %v\nOriginal error: %v",
			pkgPath, err, originalErr)
	}

	result, err := parsePackageDocs(ctx, actualPkgPath, pkgDir, symbolName, pkgPath)
	if err != nil {
		return nil, fmt.Errorf("failed to parse documentation after download: %w", err)
	}

	return result, nil
}

func suggestPackages(ctx context.Context, query string) []string {
	var candidates []string
	seen := make(map[string]bool)

	// Helper to add unique candidates
	add := func(out []byte) {
		for _, pkg := range strings.Split(strings.TrimSpace(string(out)), "\n") {
			if pkg != "" && !seen[pkg] {
				candidates = append(candidates, pkg)
				seen[pkg] = true
			}
		}
	}

	// 1. Standard Library (Reliable, works everywhere)
	if out, err := exec.CommandContext(ctx, "go", "list", "std").Output(); err == nil {
		add(out)
	}

	// 2. Local context (Context-dependent, might fail outside modules)
	if out, err := exec.CommandContext(ctx, "go", "list", "all").Output(); err == nil {
		add(out)
	}

	// 3. Parent context (If query is a path, try listing sibling packages)
	if parts := strings.Split(query, "/"); len(parts) > 1 {
		parent := strings.Join(parts[:len(parts)-1], "/")
		// Attempt to list sub-packages of the parent
		if out, err := exec.CommandContext(ctx, "go", "list", parent+"/...").Output(); err == nil {
			add(out)
		}
	}

	return findFuzzyMatches(query, candidates)
}

// ListSubPackages finds sub-packages within a directory using go list.
func ListSubPackages(ctx context.Context, pkgDir string) []string {
	cmd := exec.CommandContext(ctx, "go", "list", "-f", "{{.ImportPath}}", "./...")
	cmd.Dir = pkgDir
	out, err := cmd.Output()
	if err != nil {
		return nil
	}

	trimmed := strings.TrimSpace(string(out))
	if trimmed == "" {
		return nil
	}
	return strings.Split(trimmed, "\n")
}

func setupTempModule(ctx context.Context) (string, error) {
	tempDir, err := os.MkdirTemp("", "godoctor_docs_*")
	if err != nil {
		return "", fmt.Errorf("failed to create temp dir: %w", err)
	}

	initCmd := exec.CommandContext(ctx, "go", "mod", "init", "temp_docs_fetcher")
	initCmd.Dir = tempDir
	if out, err := initCmd.CombinedOutput(); err != nil {
		_ = os.RemoveAll(tempDir)
		return "", fmt.Errorf("failed to init temp module: %v\nOutput: %s", err, out)
	}
	return tempDir, nil
}

var vanityImportRe = regexp.MustCompile(`module declares its path as:\s+([^\s]+)`)

func downloadPackage(ctx context.Context, tempDir, pkgPath string) (string, string, error) {
	getCmd := exec.CommandContext(ctx, "go", "get", pkgPath)
	getCmd.Dir = tempDir
	out, err := getCmd.CombinedOutput()

	actualPath := pkgPath

	if err != nil {
		// Check for vanity import error
		matches := vanityImportRe.FindSubmatch(out)
		if len(matches) > 1 {
			actualPath = string(matches[1])
			// Retry with correct path
			//nolint:gosec // G204: Subprocess launched with variable is expected behavior.
			retryCmd := exec.CommandContext(ctx, "go", "get", actualPath)
			retryCmd.Dir = tempDir
			if retryOut, retryErr := retryCmd.CombinedOutput(); retryErr != nil {
				return "", "", fmt.Errorf("go get failed after vanity retry: %v\nOutput: %s", retryErr, retryOut)
			}
			// Success on retry
		} else {
			return "", "", fmt.Errorf("go get failed: %v\nOutput: %s", err, out)
		}
	}

	// Try to locate as a package first
	//nolint:gosec // G204: Subprocess launched with variable is expected behavior.
	listCmd := exec.CommandContext(ctx, "go", "list", "-f", "{{.Dir}}", actualPath)
	listCmd.Dir = tempDir
	out, err = listCmd.CombinedOutput()
	if err == nil {
		return strings.TrimSpace(string(out)), actualPath, nil
	}

	// If failed, try to locate as a module (e.g. root of repo with no root package files)
	//nolint:gosec // G204: Subprocess launched with variable is expected behavior.
	modCmd := exec.CommandContext(ctx, "go", "list", "-m", "-f", "{{.Dir}}", actualPath)
	modCmd.Dir = tempDir
	out, err = modCmd.CombinedOutput()
	if err != nil {
		return "", "", fmt.Errorf("failed to locate package or module: %v\nOutput: %s", err, out)
	}

	return strings.TrimSpace(string(out)), actualPath, nil
}
