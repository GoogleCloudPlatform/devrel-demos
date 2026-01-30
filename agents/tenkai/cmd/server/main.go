package main

import (
	"log"
	"os"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/cli"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
)

func main() {
	cw, err := os.Getwd()
	if err != nil {
		log.Fatalf("Failed to get current working directory: %v", err)
	}

	cli.SetupLogging(cw)

	database, err := cli.InitDB(cw)
	if err != nil {
		log.Fatalf("Failed to open database: %v", err)
	}
	defer database.Close()

	flags := cli.ParseFlags()

	// Dispatch based on flags.
	// 1. If --config is present, we act as the Orchestrator (ModeServer).
	if *flags.ConfigPath != "" {
		cfg, overrideNotes, err := cli.LoadAndOverrideConfig(flags)
		if err != nil {
			log.Fatalf("Failed to load config: %v", err)
		}

		cli.RunExperiment(database, cw, cfg, overrideNotes, runner.ModeServer, flags)
		return
	}

	// 2. Otherwise run Web Server
	port := 8080
	if *flags.Port > 0 {
		port = *flags.Port
	}
	// Fallback to Env if flags not passed
	if *flags.Port == 8080 && os.Getenv("PORT") != "" {
		// parsedFlags already handles defaultPort from Env, so *flags.Port is correct.
	}

	concurrent := 10
	if *flags.Concurrent > 0 {
		concurrent = *flags.Concurrent
	}

	log.Println("Starting Tenkai Server (Web UI)...")
	cli.RunServer(database, cw, port, concurrent, runner.ModeServer)
}
