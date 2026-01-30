package cli

import (
	"flag"
	"fmt"
	"log"
	"os"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/report"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
)

func Execute() {
	flags := ParseFlags()

	cwd, err := os.Getwd()
	if err != nil {
		log.Printf("Failed to get current working directory: %v", err)
		os.Exit(1)
	}

	SetupLogging(cwd)

	database, err := InitDB(cwd)
	if err != nil {
		log.Printf("Failed to open database: %v", err)
		os.Exit(1)
	}
	defer database.Close()
	cleanupOrphanExperiments(database)

	if *flags.Serve {
		// Legacy local serve (ModeLocal)
		RunServer(database, cwd, *flags.Port, *flags.Concurrent, runner.ModeLocal)
		return
	}

	if *flags.Worker {
		concurrency := 1
		if *flags.Concurrent > 0 {
			concurrency = *flags.Concurrent
		}
		RunWorker(database, cwd, concurrency, *flags.Port, *flags.GCSBucket)
		return
	}

	if *flags.FixReportPath != "" {
		if err := report.FixMarkdownReport(*flags.FixReportPath); err != nil {
			log.Printf("Failed to fix report: %v", err)
			os.Exit(1)
		}
		fmt.Printf("Successfully fixed report structure at: %s\n", *flags.FixReportPath)
		return
	}

	if *flags.ExperimentID > 0 && flag.NArg() == 0 && *flags.ConfigPath == "" {
		handleReportOnly(database, *flags.ExperimentID)
		return
	}

	if *flags.RevalID > 0 {
		handleReevaluation(database, cwd, *flags.RevalID)
		return
	}

	if *flags.ConfigPath == "" {
		fmt.Println("Usage: tenkai --config <path_to_config_yaml> [options]")
		fmt.Println("       tenkai --serve [--port 8080]")
		fmt.Printf("Tip: Check 'experiments/templates/' directory for examples\n")
		flag.PrintDefaults()
		os.Exit(1)
	}

	cfg, overrideNotes, err := LoadAndOverrideConfig(flags)
	if err != nil {
		log.Printf("Failed to load config: %v", err)
		os.Exit(1)
	}

	RunExperiment(database, cwd, cfg, overrideNotes, runner.ModeLocal, flags)
}
