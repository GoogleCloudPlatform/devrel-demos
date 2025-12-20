package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var Version = "dev"

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print the version number of tq",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("tq version %s\n", Version)
	},
}

func init() {
	rootCmd.AddCommand(versionCmd)
}
