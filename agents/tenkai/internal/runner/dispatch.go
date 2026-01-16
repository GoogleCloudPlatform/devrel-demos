package runner

import (
	"context"
	"fmt"
	"log"
	"path/filepath"
	"sync"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
)

type runContext struct {
	Ctx             context.Context
	ExperimentDir   string
	Timeout         time.Duration
	Timestamp       time.Time
	ExperiementName string
	ResultsChan     chan<- Result
	Wg              *sync.WaitGroup
	Sem             chan struct{}
}

// DispatchAll schedules all jobs for the experiment using an interleaved strategy.
func (r *Runner) DispatchAll(rc *runContext, cfg *config.Configuration) {
	// Interleaved distribution: Repetitions -> Scenarios -> Alternatives
	// This ensures even distribution of work across alternatives when concurrency is limited.
	for i := 1; i <= cfg.Repetitions; i++ {
		for _, scenPath := range cfg.Scenarios {
			for _, alt := range cfg.Alternatives {
				r.dispatchJob(rc, alt, scenPath, i)
			}
		}
	}
}

func (r *Runner) dispatchJob(rc *runContext, alt config.Alternative, scenPath string, rep int) {
	// Determine scenario identifier from path basename
	scenID := filepath.Base(scenPath)

	// Insert "Queued" status
	var runID int64
	var lastErr error
	if r.db != nil && r.experimentID != 0 {
		prerun := &models.RunResult{
			ExperimentID: r.experimentID,
			Alternative:  alt.Name,
			Scenario:     scenID,
			Repetition:   rep,
			Status:       db.RunStatusQueued,
		}
		// Retry logic for DB contention with exponential backoff
		delay := 100 * time.Millisecond
		for attempt := 0; attempt < 10; attempt++ {
			if id, err := r.db.SaveRunResult(prerun); err == nil {
				runID = id
				break
			} else {
				lastErr = err
				log.Printf("Warning: failed to save initial run state (attempt %d/10): %v. Retrying in %v...", attempt+1, err, delay)
				time.Sleep(delay)
				delay *= 2
			}
		}
		if runID == 0 {
			log.Printf("CRITICAL: Failed to persist run state for %s rep %d after retries: %v", alt.Name, rep, lastErr)
			// Mark as failed in stream to ensure experiment finishes with correct count
			rc.ResultsChan <- Result{
				Alternative: alt.Name,
				Scenario:    scenID,
				Repetition:  rep,
				Status:      db.RunStatusCompleted,
				Reason:      db.ReasonFailedError,
				ErrorStr:    fmt.Sprintf("Failed to initialize run in database: %v", lastErr),
			}
			return
		}
	}

	rc.Wg.Add(1)
	go func(alt config.Alternative, sID string, path string, rep int, dbRunID int64) {
		defer rc.Wg.Done()
		// Check for stop BEFORE acquiring semaphore
		action := r.checkAction()
		if action == "stop" {
			return
		}

		select {
		case rc.Sem <- struct{}{}:
			defer func() { <-rc.Sem }()
		case <-rc.Ctx.Done():
			return
		}
		// Mark as RUNNING just before execution
		if r.db != nil && dbRunID != 0 {
			// Retry logic for Updating Status
			delay := 50 * time.Millisecond
			for attempt := 0; attempt < 5; attempt++ {
				if err := r.db.UpdateRunStatus(dbRunID, db.RunStatusRunning); err == nil {
					break
				} else {
					log.Printf("Warning: failed to update run status to RUNNING (attempt %d/5): %v", attempt+1, err)
					time.Sleep(delay)
					delay *= 2
				}
			}
		}

		res := r.runSingle(rc.Ctx, alt, sID, rep, rc.ExperimentDir, rc.Timeout, dbRunID)
		rc.ResultsChan <- res
	}(alt, scenID, scenPath, rep, runID)
}