package collector

import (
	"context"
	"database/sql"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"path/filepath"
	"strings"
	"os"

	"golang.org/x/tools/cover"
	"golang.org/x/mod/modfile"
)

// CoverageResult represents the structure of a coverage result
type CoverageResult struct {
	Package         string `json:"package"`
	File            string `json:"file"`
	StartLine       int    `json:"start_line"`
	StartColumn     int    `json:"start_col"`
	EndLine         int    `json:"end_line"`
	EndColumn       int    `json:"end_col"`
	StatementNumber int    `json:"stmt_num"`
	Count           int    `json:"count"`
	FunctionName    string `json:"function_name"`
}

func collectCoverageResults(pkgDirs []string) ([]CoverageResult, error) {
	profiles, err := cover.ParseProfiles("coverage.out")
	if err != nil {
		return nil, fmt.Errorf("failed to parse coverage profiles: %w", err)
	}

	var results []CoverageResult
	for _, profile := range profiles {
		functionFinder, err := newFunctionFinder(profile.FileName)
		if err != nil {
			return nil, fmt.Errorf("failed to create function finder: %w", err)
		}

		for _, block := range profile.Blocks {
			results = append(results, CoverageResult{
				Package:         profile.FileName,
				File:            profile.FileName,
				StartLine:       block.StartLine,
				StartColumn:     block.StartCol,
				EndLine:         block.EndLine,
				EndColumn:       block.EndCol,
				StatementNumber: block.NumStmt,
				Count:           block.Count,
				FunctionName:    functionFinder.findFunction(block.StartLine),
			})
		}
	}

	return results, nil
}

func PopulateCoverageResults(ctx context.Context, db *sql.DB, pkgDirs []string) error {
	coverageResults, err := collectCoverageResults(pkgDirs)
	if err != nil {
		return fmt.Errorf("failed to collect coverage results: %w", err)
	}

	stmt, err := db.PrepareContext(ctx, `INSERT INTO all_coverage (package, file, start_line, start_col, end_line, end_col, stmt_num, count, function_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);`)
	if err != nil {
		return fmt.Errorf("failed to prepare statement: %w", err)
	}
	defer stmt.Close()

	for _, result := range coverageResults {
		_, err := stmt.ExecContext(ctx, result.Package, result.File, result.StartLine, result.StartColumn, result.EndLine, result.EndColumn, result.StatementNumber, result.Count, result.FunctionName)
		if err != nil {
			return fmt.Errorf("failed to insert coverage results: %w", err)
		}
	}
	return nil
}

type functionFinder struct {
	fset         *token.FileSet
	file         *ast.File
	functions    []*ast.FuncDecl
	lineMap      map[int]string
	packagePath  string
	fullFilePath string
}

func newFunctionFinder(fileName string) (*functionFinder, error) {
	var fullFilePath string
	if filepath.IsAbs(fileName) {
		fullFilePath = fileName
	} else {
		// In some cases, the file name in the coverage profile is relative to the package directory.
		// We need to find the absolute path to the file.
		// A simple way to find the project root is to look for the go.mod file
		var projectRoot string
		dir, err := os.Getwd()
		if err != nil {
			return nil, fmt.Errorf("failed to get current directory: %w", err)
		}
		for {
			if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
				projectRoot = dir
				break
			}
			if dir == filepath.Dir(dir) { // root of the filesystem
				break
			}
			dir = filepath.Dir(dir)
		}

		if projectRoot == "" {
			return nil, fmt.Errorf("failed to find project root")
		}

		// The fileName is often in the form of `package/path/to/file.go`
		// We need to join this with the project root to get the full path.
		// For example, if projectRoot is `/path/to/project` and fileName is `cmd/root.go`,
		// the full path should be `/path/to/project/cmd/root.go`.
		// However, the fileName can also be just `file.go` if the package is the root of the project.
		// So we need to handle both cases.
		// Let's try to join the project root with the fileName and see if the file exists.
		// If it does, we have our full path.
		// If not, we'll have to search for the file.
		goModFile, err := os.ReadFile(filepath.Join(projectRoot, "go.mod"))
		if err != nil {
			return nil, fmt.Errorf("failed to read go.mod file: %w", err)
		}
		modulePath := modfile.ModulePath(goModFile)

		fullFilePath = filepath.Join(projectRoot, strings.TrimPrefix(fileName, modulePath+"/"))
		if _, err := os.Stat(fullFilePath); err != nil {
			// The file does not exist at the joined path.
			// Let's search for the file in the project root.
			var found bool
			err := filepath.Walk(projectRoot, func(path string, info os.FileInfo, err error) error {
				if err != nil {
					return err
				}
				if strings.HasSuffix(path, fileName) {
					fullFilePath, err = filepath.Abs(path)
					if err != nil {
						return err
					}
					found = true
					return filepath.SkipDir
				}
				return nil
			})
			if err != nil {
				return nil, fmt.Errorf("failed to find file %s: %w", fileName, err)
			}
			if !found {
				return nil, fmt.Errorf("failed to find file %s in %s", fileName, projectRoot)
			}
		}
	}

	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, fullFilePath, nil, 0)
	if err != nil {
		return nil, fmt.Errorf("failed to parse file %s: %w", fullFilePath, err)
	}

	return &functionFinder{
		fset:         fset,
		file:         file,
		lineMap:      make(map[int]string),
		packagePath:  "",
		fullFilePath: fullFilePath,
	}, nil
}

func (f *functionFinder) findFunction(line int) string {
	if fn, ok := f.lineMap[line]; ok {
		return fn
	}

	var funcName string
	ast.Inspect(f.file, func(n ast.Node) bool {
		if fn, ok := n.(*ast.FuncDecl); ok {
			startLine := f.fset.Position(fn.Pos()).Line
			endLine := f.fset.Position(fn.End()).Line
			if line >= startLine && line <= endLine {
				funcName = fn.Name.Name
				// Map all lines within the function to the function name for faster lookups.
				for i := startLine; i <= endLine; i++ {
					f.lineMap[i] = funcName
				}
				return false // Stop searching
			}
		}
		return true // Continue searching
	})

	return funcName
}
