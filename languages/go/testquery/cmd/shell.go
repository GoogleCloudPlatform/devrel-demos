package cmd

import (
	"context"
	"database/sql"
	"fmt"
	"os"

	"github.com/danicat/testquery/internal/shell"
	_ "github.com/mattn/go-sqlite3"
	"github.com/spf13/cobra"
)

var shellCmd = &cobra.Command{
	Use:   "shell",
	Short: "Start an interactive SQL shell.",
	Long:  `Starts an interactive SQL shell to query the test database.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		dbFile, _ := cmd.Flags().GetString("db")
		pkg, _ := cmd.Flags().GetString("pkg")

		if dbFile != "" && pkg != "" {
			return fmt.Errorf("cannot use --db and --pkg flags together")
		}

		if dbFile != "" {
			return runShell(dbFile)
		}

		return runShellInMemory(pkg)
	},
}

func init() {
	rootCmd.AddCommand(shellCmd)
	shellCmd.Flags().StringVar(&dbFile, "db", "", "database file name")
	shellCmd.Flags().String("pkg", "", "package specifier")
}

func runShell(dbFile string) error {
	db, err := sql.Open("sqlite3", dbFile)
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}
	defer func() {
		if err := db.Close(); err != nil {
			fmt.Printf("failed to close database: %v\n", err)
		}
	}()

	return shell.Prompt(context.Background(), db, os.Stdin, os.Stdout)
}

func runShellInMemory(pkg string) error {
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		return fmt.Errorf("failed to open in-memory database: %w", err)
	}
	defer db.Close()

	if err := RunCollect(db, pkg); err != nil {
		return fmt.Errorf("failed to collect data: %w", err)
	}

	return shell.Prompt(context.Background(), db, os.Stdin, os.Stdout)
}
