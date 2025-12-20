package cmd

import (
	"github.com/spf13/cobra"
)

var (
	dbFile string
)

var rootCmd = &cobra.Command{
	Use:   "tq",
	Short: "TestQuery is a tool for querying Go test results.",
	Long: `TestQuery (tq) is a command-line tool that allows you to query Go test results using a SQL interface.
It is designed to help developers understand and analyze tests in their projects,
especially in large and mature codebases.`,
}

func Execute() error {
	return rootCmd.Execute()
}
