package cli

import (
	"bytes"
	"fmt"
	"log"
	"os"

	"gopkg.in/yaml.v3"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/report"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func handleReportOnly(database *db.DB, expID int64) {
	cwd, err := os.Getwd()
	if err != nil {
		log.Printf("Failed to get current working directory: %v", err)
		os.Exit(1)
	}

	exp, err := database.GetExperimentByID(expID)
	if err != nil {
		log.Printf("Failed to find experiment in DB for ID %d: %v", expID, err)
		os.Exit(1)
	}

	fmt.Printf("Regenerating report for: %s (ID: %d)\n", exp.Name, exp.ID)

	dbResults, err := database.GetRunResults(exp.ID, -1, 0)
	if err != nil {
		log.Printf("Failed to fetch run results from DB: %v", err)
		os.Exit(1)
	}

	var results []runner.Result
	r := runner.New(workspace.New(cwd, "", ""), 1)
	for _, dr := range dbResults {
		results = append(results, r.FromDBRunResult(&dr))
	}

	cfg := &config.Configuration{}
	if err := yaml.Unmarshal([]byte(exp.ConfigContent), cfg); err != nil {
		log.Printf("Warning: failed to unmarshal config from DB: %v", err)
	}

	// Fetch tool counts
	toolCounts, err := database.GetExperimentToolCounts(exp.ID, "all")
	if err != nil {
		log.Printf("Warning: failed to fetch tool counts: %v", err)
	}

	rep := report.New(results, os.Stdout, cfg, []string{"Report regenerated from SQLite Database"}, toolCounts)
	println("\n--- Results ---")
	if err := rep.GenerateConsoleReport(); err != nil {
		log.Printf("Failed to generate console report: %v", err)
	}

	var buf bytes.Buffer
	if err := rep.GenerateMarkdown(&buf); err == nil {
		if err := database.UpdateExperimentReport(exp.ID, buf.String()); err != nil {
			log.Printf("Warning: failed to save report to DB: %v", err)
		}
		fmt.Printf("\nMarkdown report regenerated and saved to Database.\n")
	}

	fmt.Printf("Parsed %d results from DB\n", len(results))
	foundAlts := make(map[string]bool)
	for _, r := range results {
		foundAlts[r.Alternative] = true
	}
	altsStr := ""
	for a := range foundAlts {
		altsStr += a + " "
	}
	fmt.Printf("Found alternatives in results: %s\n", altsStr)

	var allAlts []string
	for _, a := range cfg.Alternatives {
		allAlts = append(allAlts, a.Name)
	}
	runner.CalculateSummary(results, cfg.Control, allAlts, toolCounts, runner.FilterAll)

	fmt.Printf("Database analytics for Experiment %d are now computed on-demand.\n", exp.ID)
}
