package runner

import (
	"context"
	"fmt"
	"log"
	"os"
	"strconv"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
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
		log.Printf("Warning: Worker started without ArtifactStorage. Artifacts might be lost.")
	}
	w.Runner.Mode = ModeWorker

	// 1. Update Status to RUNNING via DB
	if err := w.DB.UpdateRunStatus(runID, db.RunStatusRunning); err != nil {
		log.Printf("Error updating run status to RUNNING: %v", err)
	}

	// 2. Execute the Job
	// RunJob handles fetching config, prep, execution, and saving results (Telemetry).
	if err := w.Runner.RunJob(ctx, runID); err != nil {
		log.Printf("Job %d finished with execution error (details saved in telemetry): %v", runID, err)
		// We don't update DB here because RunJob already saved the result/error to the run_results table.
		return err
	}

	log.Printf("Worker %s completed RunID %d successfully.", w.ID, runID)
	return nil
}
