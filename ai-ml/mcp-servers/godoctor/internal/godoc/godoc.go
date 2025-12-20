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
	"strings"
)

// GetDocumentation retrieves the documentation for a package or symbol.
func GetDocumentation(ctx context.Context, pkgPath, symbolName string) (string, error) {
	// Try to find the package directory locally
	pkgDir, err := resolvePackageDir(ctx, pkgPath)
	if err != nil {
		// Fallback: try to fetch the package in a temp directory
		return fetchAndRetry(ctx, pkgPath, symbolName, err)
	}

	result, err := parsePackageDocs(ctx, pkgPath, pkgDir, symbolName)
	if err != nil {
		return "", fmt.Errorf("failed to parse documentation: %w", err)
	}

	return renderMarkdown(result), nil
}

// Example represents a code example extracted from documentation.
type Example struct {
	Name   string `json:"name"`
	Code   string `json:"code"`
	Output string `json:"output,omitempty"`
}

// StructuredDoc represents the parsed documentation.
type StructuredDoc struct {
	Package     string    `json:"package"`
	ImportPath  string    `json:"importPath"`
	SymbolName  string    `json:"symbolName,omitempty"`
	Type        string    `json:"type,omitempty"` // "function", "type", "var", "const"
	Definition  string    `json:"definition,omitempty"`
	Description string    `json:"description"`
	Examples    []Example `json:"examples,omitempty"`
	SubPackages []string  `json:"subPackages,omitempty"`
	PkgGoDevURL string    `json:"pkgGoDevURL"`
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

func parsePackageDocs(ctx context.Context, importPath, pkgDir, symbolName string) (*StructuredDoc, error) {
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

	if len(files) == 0 {
		return nil, fmt.Errorf("no files found in package %s", importPath)
	}

	// Compute documentation using all files
	targetPkg, err := doc.NewFromFiles(fset, files, importPath)
	if err != nil {
		return nil, fmt.Errorf("doc.NewFromFiles failed: %w", err)
	}

	result := &StructuredDoc{
		Package:     targetPkg.Name,
		ImportPath:  importPath,
		PkgGoDevURL: fmt.Sprintf("https://pkg.go.dev/%s", importPath),
	}

	// Always look for sub-packages
	subs := listSubPackages(ctx, pkgDir)
	for _, sub := range subs {
		if sub != importPath { // Exclude self
			result.SubPackages = append(result.SubPackages, sub)
		}
	}

	if symbolName == "" {
		result.Description = targetPkg.Doc
		result.Definition = fmt.Sprintf("package %s // import %q", targetPkg.Name, importPath)
		result.Examples = extractExamples(fset, targetPkg.Examples)
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

func findSymbol(fset *token.FileSet, pkg *doc.Package, symName string, result *StructuredDoc) (bool, []string) {
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

func checkFuncs(fset *token.FileSet, pkg *doc.Package, symName string, result *StructuredDoc, add func(string)) bool {
	for _, f := range pkg.Funcs {
		if f.Name == symName {
			populateFunc(fset, pkg, f, result)
			return true
		}
		add(f.Name)
	}
	return false
}

func checkTypes(fset *token.FileSet, pkg *doc.Package, symName string, result *StructuredDoc, add func(string)) bool {
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

func checkVars(fset *token.FileSet, pkg *doc.Package, symName string, result *StructuredDoc, add func(string)) bool {
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

func checkConsts(fset *token.FileSet, pkg *doc.Package, symName string, result *StructuredDoc, add func(string)) bool {
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

func populateFunc(fset *token.FileSet, pkg *doc.Package, f *doc.Func, result *StructuredDoc) {
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

func renderMarkdown(doc *StructuredDoc) string {
	var buf strings.Builder

	buf.WriteString(fmt.Sprintf("# %s\n\n", doc.ImportPath))

	if doc.SymbolName != "" {
		buf.WriteString(fmt.Sprintf("## %s %s\n\n", doc.Type, doc.SymbolName))
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

func fetchAndRetry(ctx context.Context, pkgPath, symbolName string, originalErr error) (string, error) {
	tempDir, err := setupTempModule(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to setup temp module: %w", err)
	}
	defer func() {
		_ = os.RemoveAll(tempDir)
	}()

	pkgDir, err := downloadPackage(ctx, tempDir, pkgPath)
	if err != nil {
		// Attempt to provide suggestions from standard library
		suggestions := suggestPackages(ctx, pkgPath)
		suggestionText := ""
		if len(suggestions) > 0 {
			suggestionText = fmt.Sprintf("\nDid you mean: %s?", strings.Join(suggestions, ", "))
		}

		return "", fmt.Errorf("failed to download package %q: %v\nOriginal error: %v%s",
			pkgPath, err, originalErr, suggestionText)
	}

	result, err := parsePackageDocs(ctx, pkgPath, pkgDir, symbolName)
	if err != nil {
		return "", fmt.Errorf("failed to parse documentation after download: %w", err)
	}

	return renderMarkdown(result), nil
}

func suggestPackages(ctx context.Context, query string) []string {
	// 'go list all' includes std, local packages, and dependencies.
	cmd := exec.CommandContext(ctx, "go", "list", "all")
	out, err := cmd.Output()
	if err != nil {
		return nil
	}

	candidates := strings.Split(strings.TrimSpace(string(out)), "\n")
	return findFuzzyMatches(query, candidates)
}

func listSubPackages(ctx context.Context, pkgDir string) []string {
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

func downloadPackage(ctx context.Context, tempDir, pkgPath string) (string, error) {
	getCmd := exec.CommandContext(ctx, "go", "get", pkgPath)
	getCmd.Dir = tempDir
	if out, err := getCmd.CombinedOutput(); err != nil {
		return "", fmt.Errorf("go get failed: %v\nOutput: %s", err, out)
	}

	listCmd := exec.CommandContext(ctx, "go", "list", "-f", "{{.Dir}}", pkgPath)
	listCmd.Dir = tempDir
	out, err := listCmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("failed to locate package: %v\nOutput: %s", err, out)
	}
	return strings.TrimSpace(string(out)), nil
}
