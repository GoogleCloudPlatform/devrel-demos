package cmd

import (
	"database/sql"
	"fmt"
	"io"
	"os"

	"github.com/danicat/testquery/internal/database"
	"github.com/danicat/testquery/internal/pkgpattern"
	"github.com/danicat/testquery/internal/query"
	_ "github.com/mattn/go-sqlite3"
	"github.com/spf13/cobra"
)

var queryCmd = &cobra.Command{
	Use:   "query [query]",
	Short: "Execute a single query.",
	Long:  `Executes a single SQL query against the test database.`,
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		dbFile, _ := cmd.Flags().GetString("db")
		pkg, _ := cmd.Flags().GetString("pkg")

		if dbFile != "" && pkg != "" {
			return fmt.Errorf("cannot use --db and --pkg flags together")
		}

		if dbFile != "" {
			return runQuery(args[0], dbFile)
		}

		return RunQueryInMemory(os.Stdout, args[0], pkg)
	},
}

func init() {
	rootCmd.AddCommand(queryCmd)
	queryCmd.Flags().StringVar(&dbFile, "db", "", "database file name")
	queryCmd.Flags().String("pkg", "", "package specifier")
}

func runQuery(q, dbFile string) error {
	db, err := sql.Open("sqlite3", dbFile)
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}
	defer func() {
		if err := db.Close(); err != nil {
			fmt.Printf("failed to close database: %v\n", err)
		}
	}()

	return query.Execute(os.Stdout, db, q)
}

func RunQueryInMemory(w io.Writer, q, pkg string) error {
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		return fmt.Errorf("failed to open in-memory database: %w", err)
	}
	defer db.Close()

	if err := RunCollect(db, pkg); err != nil {
		return fmt.Errorf("failed to collect data: %w", err)
	}

	return query.Execute(w, db, q)
}

func RunCollect(db *sql.DB, pkgSpecifier string) error {
	pkgDirs, err := pkgpattern.ListPackages(pkgSpecifier)
	if err != nil {
		return fmt.Errorf("failed to list packages: %w", err)
	}

	if err := database.CreateTables(db); err != nil {
		return fmt.Errorf("failed to create tables: %w", err)
	}

	if err := database.PopulateTables(db, pkgDirs); err != nil {
		return fmt.Errorf("failed to populate tables: %w", err)
	}

	return nil
}
