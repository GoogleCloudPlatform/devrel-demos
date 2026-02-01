package runner

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"gopkg.in/yaml.v2"
)

// Worker orchestrates the execution of a single job.

type Worker struct {
	Runner *Runner
	DB     *db.DB
	ID     string
}

// NewWorker creates a new Worker instance.
func NewWorker(r *Runner, d *db.DB, id string) *Worker {
	return &Worker{
		Runner: r,
		DB:     d,
		ID:     id,
	}
}

// Start begins the worker execution.
// In Cloud Run Jobs mode, this executes a single job defined by RUN_ID env var and exits.
func (w *Worker) Start(ctx context.Context) error {
	// Check for Re-validation Job
	if revalIDStr := os.Getenv("REVAL_EXP_ID"); revalIDStr != "" {
		revalID, err := strconv.ParseInt(revalIDStr, 10, 64)
		if err != nil {
			return fmt.Errorf("invalid REVAL_EXP_ID %q: %v", revalIDStr, err)
		}
		log.Printf("Worker %s starting Re-evaluation for Experiment ID: %d", w.ID, revalID)

		// For re-evaluation, we need a job ID for logging?
		// We can just use "reval-<expID>"
		// Note: ReEvaluateExperiment might expect scenarios to be present.
		// Dockerfile.worker now has COPY scenarios, so this should work.
		if err := w.Runner.ReEvaluateExperiment(revalID, fmt.Sprintf("reval-%d", revalID)); err != nil {
			log.Printf("Re-evaluation failed: %v", err)
			return err
		}
		log.Printf("Re-evaluation completed successfully.")
		return nil
	}

	runIDStr := os.Getenv("RUN_ID")
	if runIDStr == "" {
		return fmt.Errorf("RUN_ID environment variable not set. Worker must be started with a specific job ID.")
	}

	runID, err := strconv.ParseInt(runIDStr, 10, 64)
	if err != nil {
		return fmt.Errorf("invalid RUN_ID %q: %v", runIDStr, err)
	}

	log.Printf("Worker %s starting Job execution for RunID: %d", w.ID, runID)

	// Ensure Storage is set on Runner for artifact upload
	if w.Runner.Storage == nil {
		return fmt.Errorf("CRITICAL: Worker started without ArtifactStorage. Artifacts will be lost.")
	}
	w.Runner.Mode = ModeWorker

	// Ensure we sync artifacts back to storage even on crash/failure.
	// This captures settings.json and logs from /tmp.
	defer func() {
		// NOTE: prepare.go creates the workspace at /tmp/tenkai-exec/<runID> when
		// running on GCS Fuse (when wsPath starts with /app/assets).
		// We must use the same path here that prepare.go uses.
		wsPath := filepath.Join("/tmp/tenkai-exec", fmt.Sprintf("%d", runID))
		targetPath := filepath.Join(w.Runner.WorkspaceMgr.RunsDir, fmt.Sprintf("%d", runID))
		log.Printf("[Runner] Final artifact sync for Run %d: %s -> %s", runID, wsPath, targetPath)
		if syncErr := w.Runner.syncDir(wsPath, targetPath); syncErr != nil {
			log.Printf("[Runner] Error during final sync: %v", syncErr)
		}
		// Wait for GCS Fuse consistency
		time.Sleep(2 * time.Second)
	}()

	// 1. Update Status to RUNNING via DB
	if err := w.DB.UpdateRunStatus(runID, db.RunStatusRunning); err != nil {
		return fmt.Errorf("CRITICAL: Error updating run status to RUNNING for run %d: %w", runID, err)
	}

	// 2. Execute the Job
	// runSingle logic is what we need, but usually it's wrapped or we need to extract args from DB run record.
	// For Cloud Run Jobs, we are given a RUN_ID. The DB record already exists with Scenario, Alternative, Repetition.
	// We need to FETCH these details to invoke runSingle.

	runRes, err := w.DB.GetRunResultByID(runID)
	if err != nil {
		return fmt.Errorf("failed to fetch run details for %d: %w", runID, err)
	}

	// We need config to know the Command/Args for the alternative.
	// But RunResult only has Alternative Name.
	// We need to fetch the Experiment to get the Configuration.
	exp, err := w.DB.GetExperimentByID(runRes.ExperimentID)
	if err != nil {
		return fmt.Errorf("failed to fetch experiment %d: %w", runRes.ExperimentID, err)
	}

	// Parse Config
	var cfg config.Configuration
	if err := yaml.Unmarshal([]byte(exp.ConfigContent), &cfg); err != nil {
		return fmt.Errorf("failed to parse experiment config: %w", err)
	}

	// Find Alternative Config
	var altConfig config.Alternative
	found := false
	for _, a := range cfg.Alternatives {
		if a.Name == runRes.Alternative {
			altConfig = a
			found = true
			break
		}
	}
	if !found {
		return fmt.Errorf("alternative %q not found in experiment config", runRes.Alternative)
	}

	// Determine Scenario Path (it's just the ID/Name relative to scenarios dir)
	// runRes.Scenario is the ID/Name

	// Run Single
	// We use a reasonable timeout from config or default
	timeout := 10 * time.Minute
	if cfg.Timeout != "" {
		if d, err := time.ParseDuration(cfg.Timeout); err == nil {
			timeout = d
		}
	}

	// Ensure experiment dir concept maps to something valid for worker?
	// For Worker, experimentDir is mostly for structure. We use r.WorkspaceMgr.BasePath.
	// We can pass a dummy or BasePath as experimentDir. runSingle uses it to construct path,
	// but if ModeWorker is set, it overrides it.

	res := w.Runner.runSingle(ctx, altConfig, runRes.Scenario, runRes.Repetition, w.Runner.WorkspaceMgr.BasePath, timeout, runID)

	if res.ErrorStr != "" {
		return fmt.Errorf("run failed: %s", res.ErrorStr)
	}

	log.Printf("Worker %s completed RunID %d successfully.", w.ID, runID)
	return nil
}
