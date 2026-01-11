package cli

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/report"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func runExperiment(database *db.DB, cwd string, cfg *config.Configuration, overrideNotes []string) {
	timestamp := time.Now()
	experimentDir, destConfigPath, err := prepareExperimentDir(cwd, cfg, timestamp)
	if err != nil {
		log.Printf("Failed to prepare experiment dir: %v", err)
		os.Exit(1)
	}

	scenariosDir := filepath.Join(cwd, "scenarios")
	wsMgr := workspace.New(cwd, scenariosDir, scenariosDir)
	r := runner.New(wsMgr, cfg.MaxConcurrent)
	r.SetDB(database)

	effectiveConfigData, _ := os.ReadFile(destConfigPath)

	expRecord := &models.Experiment{
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
		ExecutionControl:  "",
		ExperimentControl: cfg.Control,
		PID:               os.Getpid(),
	}

	expID, err := database.CreateExperiment(expRecord)
	if err != nil {
		log.Printf("Warning: failed to register experiment in DB: %v", err)
	}
	r.SetExperimentID(expID)

	handleExperimentSignals(database, expID)

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

	if err := database.UpdateExperimentDuration(expID, int64(duration)); err != nil {
		log.Printf("Warning: failed to update experiment duration: %v", err)
	}

	fmt.Println("All jobs processed. Analytics available in Dashboard.")
	rep := report.New(results, os.Stdout, cfg, overrideNotes)
	println("\n--- Results ---")
	if err := rep.GenerateConsoleReport(); err != nil {
		log.Printf("Failed to generate console report: %v", err)
	}

	var buf bytes.Buffer
	if err := rep.GenerateMarkdown(&buf); err == nil {
		if err := database.UpdateExperimentReport(expID, buf.String()); err != nil {
			log.Printf("Warning: failed to save report to DB: %v", err)
		}
	}

	fmt.Println("Experiment execution finished.")
}

func handleExperimentSignals(database *db.DB, expID int64) {
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-c
		fmt.Println("\n[Tenkai] Received interrupt signal. Shutting down...")
		if expID != 0 {
			if err := database.UpdateExperimentStatus(expID, db.ExperimentStatusAborted); err != nil {
				log.Printf("Failed to update status to ABORTED: %v", err)
			}
			if err := database.UpdateExperimentError(expID, "Process terminated by user/system"); err != nil {
				log.Printf("Failed to update error message: %v", err)
			}

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
}
