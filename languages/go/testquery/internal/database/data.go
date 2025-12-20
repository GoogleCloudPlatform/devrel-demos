package database

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/danicat/testquery/internal/collector"
	_ "embed"
)

//go:embed sql/schema.sql
var DDL string

func CreateTables(db *sql.DB) error {
	_, err := db.Exec(DDL)
	return err
}

func PopulateTables(db *sql.DB, pkgDirs []string) error {
	testResults, err := collector.PopulateTestResults(context.Background(), db, pkgDirs)
	if err != nil {
		return fmt.Errorf("failed to populate test results: %w", err)
	}

	if err := collector.PopulateCoverageResults(context.Background(), db, pkgDirs); err != nil {
		return fmt.Errorf("failed to populate coverage results: %w", err)
	}

	if err := collector.PopulateTestCoverageResults(context.Background(), db, pkgDirs, testResults); err != nil {
		return fmt.Errorf("failed to populate test coverage results: %w", err)
	}

	if err := collector.PopulateCode(context.Background(), db, pkgDirs); err != nil {
		return fmt.Errorf("failed to populate code: %w", err)
	}

	return nil
}

func PersistDatabase(db *sql.DB, dbFile string) error {
	_, err := db.Exec("VACUUM INTO ?", dbFile)
	if err != nil {
		return fmt.Errorf("failed to save database file: %w", err)
	}

	return nil
}
