package cli

import (
	"bytes"
	"context"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"gopkg.in/yaml.v3"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/report"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/server"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func Execute() {
	configPath := flag.String("config", "", "Path to configuration file")
	serveFlag := flag.Bool("serve", false, "Run as API server")
	portFlag := flag.Int("port", 8080, "Port for API server")
	repsFlag := flag.Int("reps", 0, "Override number of repetitions")
	concurrentFlag := flag.Int("concurrent", 0, "Override max concurrent workers")
	nameFlag := flag.String("name", "", "Override experiment name")
	altsFlag := flag.String("alternatives", "", "Comma-separated list of alternatives to run")
	scensFlag := flag.String("scenarios", "", "Comma-separated list of scenarios to run")
	controlFlag := flag.String("control", "", "Name of the control alternative")
	timeoutFlag := flag.String("timeout", "", "Override timeout duration (e.g. 5m)")
	experimentID := flag.Int64("experiment-id", 0, "Experiment ID to regenerate report")
	fixReportPath := flag.String("fix-report", "", "Path to existing report.md to fix structure/formatting")
	flag.Parse()

	cwd, err := os.Getwd()
	if err != nil {
		log.Printf("Failed to get current working directory: %v", err)
		os.Exit(1)
	}

	// 0.5 Setup Application Logging
	logFilePath := filepath.Join(cwd, "tenkai.log")
	logFile, err := os.OpenFile(logFilePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err == nil {
		mw := io.MultiWriter(os.Stdout, logFile)
		log.SetOutput(mw)
	} else {
		fmt.Printf("Warning: failed to create tenkai.log: %v\n", err)
	}

	// Initialize Database and cleanup Orphans
	dbPath := filepath.Join(cwd, "experiments", "tenkai.db")
	database, err := db.Open(dbPath)
	if err != nil {
		log.Printf("Failed to open database: %v", err)
		os.Exit(1)
	}
	defer database.Close()
	cleanupOrphanExperiments(database)

	// Handle Server Mode
	if *serveFlag {
		runServer(database, cwd, *portFlag, *concurrentFlag)
		return
	}

	// Handle Report Fixer Mode
	if *fixReportPath != "" {
		if err := report.FixMarkdownReport(*fixReportPath); err != nil {
			log.Printf("Failed to fix report: %v", err)
			os.Exit(1)
		}
		fmt.Printf("Successfully fixed report structure at: %s\n", *fixReportPath)
		return
	}

	// Handle Report-Only Mode
	if *experimentID > 0 && flag.NArg() == 0 && *configPath == "" {
		handleReportOnly(database, *experimentID)
		return
	}

	if *configPath == "" {
		fmt.Println("Usage: tenkai --config <path_to_config_yaml> [options]")
		fmt.Println("       tenkai --serve [--port 8080]")
		fmt.Printf("Tip: Check 'experiments/templates/' directory for examples\n")
		flag.PrintDefaults()
		os.Exit(1)
	}

	// 1. Load Configuration
	cfg, err := config.Load(*configPath)
	if err != nil {
		log.Printf("Failed to load config: %v", err)
		os.Exit(1)
	}

	// Apply CLI overrides
	var overrideNotes []string
	if *repsFlag > 0 {
		if *repsFlag != cfg.Repetitions {
			overrideNotes = append(overrideNotes, fmt.Sprintf("⚠️ Repetitions overridden to %d via CLI (config: %d)", *repsFlag, cfg.Repetitions))
		}
		cfg.Repetitions = *repsFlag
	}
	if *concurrentFlag > 0 {
		if *concurrentFlag != cfg.MaxConcurrent {
			overrideNotes = append(overrideNotes, fmt.Sprintf("⚠️ Max concurrent workers overridden to %d via CLI (config: %d)", *concurrentFlag, cfg.MaxConcurrent))
		}
		cfg.MaxConcurrent = *concurrentFlag
	}
	if *nameFlag != "" {
		cfg.Name = *nameFlag
	}
	if *controlFlag != "" {
		cfg.Control = *controlFlag
	}
	if *timeoutFlag != "" {
		// validate duration format
		if _, err := time.ParseDuration(*timeoutFlag); err != nil {
			log.Printf("Invalid timeout format %q: %v", *timeoutFlag, err)
			os.Exit(1)
		}
		cfg.Timeout = *timeoutFlag
		overrideNotes = append(overrideNotes, fmt.Sprintf("⏱️ Timeout overridden to %s via CLI", *timeoutFlag))
	}

	// Apply Filters
	if *altsFlag != "" {
		alts := strings.Split(*altsFlag, ",")
		var filtered []config.Alternative
		for _, name := range alts {
			name = strings.TrimSpace(name)
			for _, a := range cfg.Alternatives {
				if a.Name == name {
					filtered = append(filtered, a)
					break
				}
			}
		}
		if len(filtered) > 0 {
			// Only report if we actually filtered something out
			if len(filtered) < len(cfg.Alternatives) {
				overrideNotes = append(overrideNotes, fmt.Sprintf("🎯 Alternatives filtered to: %s", *altsFlag))
			}
			cfg.Alternatives = filtered
		}
	}

	if *scensFlag != "" {
		scens := strings.Split(*scensFlag, ",")
		var filtered []string
		for _, name := range scens {
			name = strings.TrimSpace(name)
			for _, s := range cfg.Scenarios {
				// Match against full path or basename
				if s == name || filepath.Base(s) == name {
					filtered = append(filtered, s)
					break
				}
			}
		}
		if len(filtered) > 0 {
			// Only report if we actually filtered something out
			if len(filtered) < len(cfg.Scenarios) {
				overrideNotes = append(overrideNotes, fmt.Sprintf("🎯 Scenarios filtered to: %s", *scensFlag))
			}
			cfg.Scenarios = filtered
		}
	}

	// 2. Prepare Output Directory
	timestamp := time.Now()
	tsStr := timestamp.Format("20060102-150405")
	folderName := tsStr
	if cfg.Name != "" {
		folderName = fmt.Sprintf("%s_%s", tsStr, cfg.Name)
	}

	// Determine experiment directory: <cwd>/experiments/runs/<folderName>
	experimentDir := filepath.Join(cwd, "experiments", "runs", folderName)
	if err := os.MkdirAll(experimentDir, 0755); err != nil {
		log.Printf("Failed to create experiment dir: %v", err)
		os.Exit(1)
	}

	// NEW: Marshal Effective Config to YAML
	effectiveConfigData, err := yaml.Marshal(cfg)
	if err != nil {
		log.Printf("Failed to marshal effective config: %v", err)
		os.Exit(1)
	}

	// Save Config to Output Dir
	destConfigPath := filepath.Join(experimentDir, "config.yaml")
	if err := os.WriteFile(destConfigPath, effectiveConfigData, 0644); err != nil {
		log.Printf("Warning: failed to write config file: %v", err)
	} else {
		fmt.Printf("Configuration saved to: %s\n", destConfigPath)
	}

	// 3. Initialize Dependencies
	scenariosDir := filepath.Join(cwd, "scenarios")
	wsMgr := workspace.New(cwd, scenariosDir, scenariosDir)

	r := runner.New(wsMgr, cfg.MaxConcurrent)
	r.SetDB(database) // Inject DB into runner

	// 4. Register Experiment in DB (Initial status: running)
	expRecord := &db.Experiment{
		Timestamp:         timestamp,
		Name:              cfg.Name,
		ConfigPath:        destConfigPath,
		Status:            db.ExperimentStatusRunning,
		Reps:              cfg.Repetitions,
		Concurrent:        cfg.MaxConcurrent,
		TotalJobs:         cfg.Repetitions * len(cfg.Alternatives) * len(cfg.Scenarios),
		CompletedJobs:     0,
		Description:       cfg.Description,
		ConfigContent:     string(effectiveConfigData),
		ExecutionControl:  "", // Signals are empty by default
		ExperimentControl: cfg.Control,
		PID:               os.Getpid(),
	}

	expID, err := database.CreateExperiment(expRecord)
	if err != nil {
		log.Printf("Warning: failed to register experiment in DB: %v", err)
	}
	r.SetExperimentID(expID) // Set ID for result correlation

	// Setup Signal Handling for Graceful Shutdown
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-c
		fmt.Println("\n[Tenkai] Received interrupt signal. Shutting down...")
		fmt.Println("\n[Tenkai] Received interrupt signal. Shutting down...")
		if expID != 0 {
			if err := database.UpdateExperimentStatus(expID, db.ExperimentStatusAborted); err != nil {
				log.Printf("Failed to update status to ABORTED: %v", err)
			}
			if err := database.UpdateExperimentError(expID, "Process terminated by user/system"); err != nil {
				log.Printf("Failed to update error message: %v", err)
			}

			// Mark incomplete runs as INTERRUPTED
			results, err := database.GetRunResults(expID, -1, 0)
			if err == nil {
				for _, r := range results {
					st := strings.ToUpper(r.Status)
					if st == db.RunStatusRunning || st == db.RunStatusQueued {
						database.UpdateRunStatus(r.ID, "FAILED (INTERRUPTED)")
					}
				}
			}
		}
		os.Exit(1)
	}()

	// 5. Run Experiments
	fmt.Printf("Starting Tenkai experiment with %d repetition(s) and %d concurrent worker(s)...\n", cfg.Repetitions, cfg.MaxConcurrent)
	fmt.Printf("Output Directory: %s\n", experimentDir)

	results, err := r.Run(context.Background(), cfg, timestamp, experimentDir)
	if err != nil {
		database.UpdateExperimentError(expID, err.Error())
		database.UpdateExperimentStatus(expID, db.ExperimentStatusAborted)
		log.Printf("Experiment run failed: %v", err)
		os.Exit(1)
	}

	duration := time.Since(timestamp)
	fmt.Printf("\nExperiment completed in %s.\n", duration.Round(time.Millisecond))

	// Update DB with duration
	if err := database.UpdateExperimentDuration(expID, int64(duration)); err != nil {
		log.Printf("Warning: failed to update experiment duration: %v", err)
	}

	fmt.Println("All jobs processed. Analytics available in Dashboard.")
	// 7. Generate & Save Report (both console and markdown for DB)
	rep := report.New(results, os.Stdout, cfg, overrideNotes)
	println("\n--- Results ---")
	rep.GenerateConsoleReport()

	var buf bytes.Buffer
	if err := rep.GenerateMarkdown(&buf); err == nil {
		if err := database.UpdateExperimentReport(expID, buf.String()); err != nil {
			log.Printf("Warning: failed to save report to DB: %v", err)
		}
	}

	fmt.Println("Experiment execution finished.")
}

func runServer(database *db.DB, cwd string, port int, concurrent int) {
	scenariosDir := filepath.Join(cwd, "scenarios")
	wsMgr := workspace.New(cwd, scenariosDir, scenariosDir)

	// Default to 4 concurrent if not specified
	if concurrent <= 0 {
		concurrent = 4
	}

	r := runner.New(wsMgr, concurrent)
	r.SetDB(database)

	srv := server.New(database, r, wsMgr)

	// Capture interrupt for graceful server shutdown
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-c
		fmt.Println("\n[Tenkai Server] Shutting down...")
		os.Exit(0)
	}()

	if err := srv.Start(port); err != nil {
		log.Printf("Server failed: %v", err)
		os.Exit(1)
	}
}

func handleReportOnly(database *db.DB, expID int64) {
	cwd, err := os.Getwd()
	if err != nil {
		log.Printf("Failed to get current working directory: %v", err)
		os.Exit(1)
	}

	// 1. Resolve Experiment
	exp, err := database.GetExperimentByID(expID)
	if err != nil {
		log.Printf("Failed to find experiment in DB for ID %d: %v", expID, err)
		os.Exit(1)
	}

	fmt.Printf("Regenerating report for: %s (ID: %d)\n", exp.Name, exp.ID)

	// 2. Fetch Results from DB
	dbResults, err := database.GetRunResults(exp.ID, -1, 0)
	if err != nil {
		log.Printf("Failed to fetch run results from DB: %v", err)
		os.Exit(1)
	}
	// 3. Convert DB Results to Runner Results
	var results []runner.Result
	r := runner.New(workspace.New(cwd, "", ""), 1) // Minimal runner for helper usage
	for _, dr := range dbResults {
		results = append(results, r.FromDBRunResult(&dr))
	}

	// 4. Load Config (from DB)
	cfg := &config.Configuration{}
	if err := yaml.Unmarshal([]byte(exp.ConfigContent), cfg); err != nil {
		log.Printf("Warning: failed to unmarshal config from DB: %v", err)
	}

	// 5. Generate & Save Report
	rep := report.New(results, os.Stdout, cfg, []string{"Report regenerated from SQLite Database"})
	println("\n--- Results ---")
	rep.GenerateConsoleReport()

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
	// 6. Calculate and Display Summaries
	var allAlts []string
	for _, a := range cfg.Alternatives {
		allAlts = append(allAlts, a.Name)
	}
	runner.CalculateSummary(results, cfg.Control, allAlts)

	fmt.Printf("Database analytics for Experiment %d are now computed on-demand.\n", exp.ID)
}

func cleanupOrphanExperiments(database *db.DB) {
	// Find all experiments in RUNNING state
	experiments, err := database.GetExperiments()
	if err != nil {
		return
	}

	for _, exp := range experiments {
		status := strings.ToUpper(exp.Status)
		if status == db.ExperimentStatusRunning {
			// Check if PID is alive
			if exp.PID <= 0 {
				continue
			}

			// On Unix, FindProcess always succeeds, we must call Signal(0)
			process, err := os.FindProcess(exp.PID)
			if err != nil {
				markAbortedSpeculative(database, exp)
				continue
			}

			err = process.Signal(syscall.Signal(0))
			if err != nil {
				// Signal 0 failed, process is likely dead
				markAbortedSpeculative(database, exp)
			}
		}
	}
}

func markAbortedSpeculative(database *db.DB, exp db.Experiment) {
	log.Printf("Detected orphaned experiment %d (PID %d is dead). Marking as ABORTED.", exp.ID, exp.PID)
	database.UpdateExperimentStatus(exp.ID, db.ExperimentStatusAborted)
	database.UpdateExperimentError(exp.ID, "Orchestrator process terminated unexpectedly")

	// Also mark non-terminal runs as ABORTED
	results, err := database.GetRunResults(exp.ID, -1, 0)
	if err == nil {
		for _, r := range results {
			st := strings.ToUpper(r.Status)
			if st == db.RunStatusRunning || st == db.RunStatusQueued {
				database.UpdateRunStatusAndReason(r.ID, db.RunStatusCompleted, db.ExperimentStatusAborted)
			}
		}
	}
}
