package collector

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type CodeLine struct {
	Package    string `json:"package"`
	File       string `json:"file"`
	LineNumber int    `json:"line_number"`
	Content    string `json:"content"`
}

// collectCodeLines collects all lines of code from Go files
func collectCodeLines(pkgDirs []string) ([]CodeLine, error) {
	var results []CodeLine

	for _, dir := range pkgDirs {
		if dir == "" {
			continue
		}
		err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return err
			}
			if !info.IsDir() && strings.HasSuffix(info.Name(), ".go") {
				packageName := filepath.Dir(path)
				fileName := filepath.Base(path)

				data, err := os.ReadFile(path)
				if err != nil {
					return fmt.Errorf("failed to read file %s: %w", path, err)
				}

				lines := strings.Split(string(data), "\n")
				for i, line := range lines {
					results = append(results, CodeLine{
						Package:    packageName,
						File:       fileName,
						LineNumber: i + 1,
						Content:    line,
					})
				}
			}
			return nil
		})
		if err != nil {
			return nil, fmt.Errorf("failed to extract lines of code from %s: %w", dir, err)
		}
	}

	return results, nil
}

func PopulateCode(ctx context.Context, db *sql.DB, pkgDirs []string) error {
	allCode, err := collectCodeLines(pkgDirs)
	if err != nil {
		return fmt.Errorf("failed to collect code lines: %w", err)
	}

	stmt, err := db.PrepareContext(ctx, `INSERT INTO all_code (package, file, line_number, content) VALUES (?, ?, ?, ?);`)
	if err != nil {
		return fmt.Errorf("failed to prepare statement: %w", err)
	}
	defer stmt.Close()

	for _, result := range allCode {
		_, err := stmt.ExecContext(ctx, result.Package, result.File, result.LineNumber, result.Content)
		if err != nil {
			return fmt.Errorf("failed to insert code line for %s/%s:%d: %w", result.Package, result.File, result.LineNumber, err)
		}
	}

	return nil
}
