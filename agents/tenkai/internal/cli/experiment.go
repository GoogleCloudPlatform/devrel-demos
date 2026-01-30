package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
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
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/report"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func RunExperiment(database *db.DB, cwd string, cfg *config.Configuration, overrideNotes []string, mode runner.RunnerMode, flags Flags) {
	timestamp := time.Now()
	// Use /tmp if running in Cloud Run (indicated by PORT env var usually, or just enforce it for robustness)
	// Actually, let's just use os.TempDir() if we can't write to cwd?
	// Or better: In Cloud Mode, we shouldn't rely on local persistent storage anyway (we use DB + GCS).
	// So writing to /tmp is safe and correct.

	baseDir := cwd
	if os.Getenv("K_SERVICE") != "" || os.Getenv("CLOUD_RUN_JOB") != "" {
		baseDir = os.TempDir()
	}
	experimentDir, destConfigPath, err := prepareExperimentDir(baseDir, cfg, timestamp)
	if err != nil {
		log.Printf("Failed to prepare experiment dir: %v", err)
		os.Exit(1)
	}

	scenariosDir := filepath.Join(cwd, "scenarios")
	wsMgr := workspace.New(cwd, scenariosDir, scenariosDir)
	r := runner.New(wsMgr, cfg.MaxConcurrent)
	r.SetMode(mode)
	r.SetDB(database)

	// INLINE ASSETS: Read external files (System Prompt, Context) and embed them into the configuration.
	// This ensures that the configuration stored in the DB is self-contained and reproducible by detached Workers.
	if err := inlineConfigurationAssets(cfg, cwd); err != nil {
		log.Printf("Warning: failed to inline assets: %v", err)
		// Proceed? Or Fail? Failing is safer for reproducibility.
		os.Exit(1)
	}

	// Re-serialize the effective config with inlined assets
	// We iterate to update config.yaml on disk? No, that modifies the template.
	// We just want the DB record to have the inlined version.
	// But `destConfigPath` points to a file we already wrote?
	// `prepareExperimentDir` writes the config. We should probably overwrite it or just use the struct for DB.
	// The variable `effectiveConfigData` below reads back the file. We should serialize `cfg` instead.

	effectiveConfigYAML, err := yaml.Marshal(cfg)
	if err != nil {
		log.Printf("Failed to marshal effective config: %v", err)
		os.Exit(1)
	}

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
		ConfigContent:     string(effectiveConfigYAML), // Store the inlined version
		ExecutionControl:  "",
		ExperimentControl: cfg.Control,
		PID:               os.Getpid(),
	}

	var expID int64
	if *flags.StartExperimentID > 0 {
		expID = *flags.StartExperimentID
		// Update existing experiment PID and Status
		// Ideally we should verify it exists.
		log.Printf("Resuming/Starting orchestration for Experiment ID: %d", expID)
		if err := database.UpdateExperimentStatus(expID, db.ExperimentStatusRunning); err != nil {
			log.Printf("Warning: failed to update status for exp %d: %v", expID, err)
		}
		// Also update ConfigPath? Maybe. But Handler created it.
		// Wait, Handler creates record. We should update PID.
		// Unfortunately UpdateFunction for PID doesn't exist yet, but we can add it or just ignore PID for now (PID used for local kill).
		// For Cloud Run, killing PID isn't the way to stop.
	} else {
		id, err := database.CreateExperiment(expRecord)
		if err != nil {
			log.Printf("Warning: failed to register experiment in DB: %v", err)
		}
		expID = id
	}
	r.SetExperimentID(expID)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	handleExperimentSignals(database, expID, cancel)

	fmt.Printf("Starting Tenkai experiment with %d repetition(s) and %d concurrent worker(s)...\n", cfg.Repetitions, cfg.MaxConcurrent)
	fmt.Printf("Output Directory: %s\n", experimentDir)

	results, err := r.Run(ctx, cfg, timestamp, experimentDir)
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

	// Fetch tool counts for report
	toolCounts, err := database.GetExperimentToolCounts(expID, "all")
	if err != nil {
		log.Printf("Warning: failed to fetch tool counts: %v", err)
	}

	fmt.Println("All jobs processed. Analytics available in Dashboard.")
	rep := report.New(results, os.Stdout, cfg, overrideNotes, toolCounts)
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

	if ctx.Err() == context.Canceled {
		os.Exit(1)
	}
}

func handleExperimentSignals(database *db.DB, expID int64, cancel context.CancelFunc) {
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
		cancel()
	}()
}

// inlineConfigurationAssets reads external files referenced in the config and embeds their content.
func inlineConfigurationAssets(cfg *config.Configuration, baseDir string) error {
	for i := range cfg.Alternatives {
		alt := &cfg.Alternatives[i]

		// 1. System Prompt
		if alt.SystemPromptFile != "" {
			path := alt.SystemPromptFile
			if !filepath.IsAbs(path) {
				path = filepath.Join(baseDir, path)
			}
			content, err := os.ReadFile(path)
			if err != nil {
				return fmt.Errorf("failed to read system prompt file %s: %w", path, err)
			}
			alt.SystemPrompt = string(content) // Embed
			// Keep path for reference, but content is now primary
		}

		// 2. Context File
		if alt.ContextFilePath != "" {
			path := alt.ContextFilePath
			if !filepath.IsAbs(path) {
				path = filepath.Join(baseDir, path)
			}
			content, err := os.ReadFile(path)
			if err != nil {
				return fmt.Errorf("failed to read context file %s: %w", path, err)
			}
			alt.Context = string(content) // Embed
		}

		// 3. Settings File
		if alt.SettingsPath != "" {
			path := alt.SettingsPath
			if !filepath.IsAbs(path) {
				path = filepath.Join(baseDir, path)
			}
			content, err := os.ReadFile(path)
			if err != nil {
				return fmt.Errorf("failed to read settings file %s: %w", path, err)
			}
			var settings map[string]interface{}
			if err := json.Unmarshal(content, &settings); err != nil {
				return fmt.Errorf("failed to parse settings file %s: %w", path, err)
			}
			// Merge/Store. We have specific fields or blocks.
			// Let's store it as a block to ensure it's applied?
			// Or just set alt.Settings if empty.
			if alt.Settings == nil {
				alt.Settings = settings
			} else {
				// If both exist, we need to merge. New block?
				// Add to start of blocks?
				// Simplest: Prepend to SettingsBlocks
				alt.SettingsBlocks = append([]map[string]interface{}{settings}, alt.SettingsBlocks...)
			}
		}
	}
	return nil
}
