package runner

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sync"
	"time"

	run "cloud.google.com/go/run/apiv2"
	runpb "cloud.google.com/go/run/apiv2/runpb"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
)

type runContext struct {
	Ctx            context.Context
	ExperimentDir  string
	Timeout        time.Duration
	Timestamp      time.Time
	ExperimentName string
	ResultsChan    chan<- Result
	Wg             *sync.WaitGroup
	Sem            chan struct{}
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
				log.Printf("Error: failed to save initial run state (attempt %d/10): %v. Retrying in %v...", attempt+1, err, delay)
				if attempt == 9 {
					log.Fatalf("CRITICAL: Failed to save initial run state after 10 attempts: %+v", lastErr)
				}
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

	// If Server mode, we trigger Cloud Run Job execution
	jobID := fmt.Sprintf("[%s|%s|#%d]", alt.Name, scenID, rep)
	if r.Mode == ModeServer {
		rc.Wg.Add(1)
		go func(alt config.Alternative, sID string, path string, rep int, dbRunID int64, jobID string) {
			defer rc.Wg.Done()

			// Acquire semaphore to limit Cloud Run concurrency
			select {
			case rc.Sem <- struct{}{}:
				defer func() { <-rc.Sem }()
			case <-rc.Ctx.Done():
				return
			}

			log.Printf("Triggering Cloud Run Job for %s (RunID: %d)", jobID, dbRunID)
			if err := r.triggerCloudRunJob(rc.Ctx, dbRunID); err != nil {
				log.Fatalf("CRITICAL: Error triggering Cloud Run Job for run %d: %v", dbRunID, err)
			}

			// Wait for completion (Polling DB)
			ticker := time.NewTicker(2 * time.Second)
			defer ticker.Stop()

			for {
				select {
				case <-rc.Ctx.Done():
					return
				case <-ticker.C:
					if r.db == nil {
						log.Fatalf("CRITICAL: DB is nil, cannot poll run %d", dbRunID)
						return
					}
					runRes, err := r.db.GetRunResultByID(dbRunID)
					if err != nil {
						log.Fatalf("CRITICAL: failed to poll run %d: %v", dbRunID, err)
						continue
					}
					if runRes.Status == db.RunStatusCompleted || runRes.Status == db.RunStatusAborted {
						log.Printf("Cloud Run Job %s completed (Status: %s)", jobID, runRes.Reason)
						// Convert to Result and send to channel
						res := r.FromDBRunResult(runRes)
						rc.ResultsChan <- res
						return
					}
				}
			}
		}(alt, scenID, scenPath, rep, runID, jobID)
		return
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
					log.Printf("Error: failed to update run status to RUNNING (attempt %d/5): %v", attempt+1, err)
					if attempt == 4 {
						log.Fatalf("CRITICAL: Failed to update run status after 5 attempts: %+v", err)
					}
					time.Sleep(delay)
					delay *= 2
				}
			}
		}

		res := r.runSingle(rc.Ctx, alt, sID, rep, rc.ExperimentDir, rc.Timeout, dbRunID)
		rc.ResultsChan <- res
	}(alt, scenID, scenPath, rep, runID)
}

func (r *Runner) triggerCloudRunJob(ctx context.Context, runID int64) error {
	// Prefer standard GCP environment variables
	project := os.Getenv("GOOGLE_CLOUD_PROJECT")
	if project == "" {
		project = os.Getenv("PROJECT_ID")
	}

	region := os.Getenv("GOOGLE_CLOUD_LOCATION")
	if region == "" {
		region = os.Getenv("REGION")
	}
	if region == "" {
		// Region is required for non-global triggers, but let's allow it to be empty
		// if we are explicitly aiming for a global endpoint.
		// However, the gcloud command usually needs a location.
		log.Printf("Warning: GOOGLE_CLOUD_LOCATION/REGION env var missing. Defaulting to us-central1 for job trigger.")
		region = "us-central1"
	}

	jobName := os.Getenv("TENKAI_JOB_NAME")

	if project == "" {
		return fmt.Errorf("missing mandatory env var: GOOGLE_CLOUD_PROJECT")
	}
	if jobName == "" {
		return fmt.Errorf("missing mandatory env var: TENKAI_JOB_NAME")
	}

	// Create client
	client, err := run.NewJobsClient(ctx)
	if err != nil {
		return fmt.Errorf("failed to create run client: %w", err)
	}
	defer client.Close()

	// Full resource name: projects/{project}/locations/{location}/jobs/{job}
	name := fmt.Sprintf("projects/%s/locations/%s/jobs/%s", project, region, jobName)

	req := &runpb.RunJobRequest{
		Name: name,
		Overrides: &runpb.RunJobRequest_Overrides{
			ContainerOverrides: []*runpb.RunJobRequest_Overrides_ContainerOverride{
				{
					Env: []*runpb.EnvVar{
						{
							Name: "RUN_ID",
							Values: &runpb.EnvVar_Value{
								Value: fmt.Sprintf("%d", runID),
							},
						},
						{
							Name: "GEMINI_API_KEY",
							Values: &runpb.EnvVar_Value{
								Value: "AIzaSyDVtKbYaP1S6yWa4nWa6FlIMQNqI5osdVI",
							},
						},
					},
				},
			},
		},
	}

	// We return the Operation, but we don't wait for it to complete.
	// The Worker updates the DB, and the Runner Loop polls the DB.
	op, err := client.RunJob(ctx, req)
	if err != nil {
		return fmt.Errorf("failed to call RunJob: %w", err)
	}

	log.Printf("Cloud Run Job triggered: %s (Operation: %s)", name, op.Name())
	return nil
}
