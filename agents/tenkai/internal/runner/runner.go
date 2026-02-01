package runner

import (
	"context"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/parser"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/storage"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

type RunnerMode string

const (
	ModeLocal  RunnerMode = "local"
	ModeServer RunnerMode = "server"
	ModeWorker RunnerMode = "worker"
)

type Result struct {
	RunID             int64
	Alternative       string
	Scenario          string
	Repetition        int
	Status            string
	Reason            string
	Duration          time.Duration
	ErrorStr          string
	IsSuccess         bool
	ValidationReport  string
	AgentMetrics      *parser.AgentMetrics
	EvaluationMetrics *models.EvaluationMetrics
}

type Runner struct {
	WorkspaceMgr *workspace.Manager
	concurrency  int
	Mode         RunnerMode
	db           *db.DB
	experimentID int64
	Storage      storage.Storage
}

func New(wsMgr *workspace.Manager, concurrency int) *Runner {

	if concurrency <= 0 {
		concurrency = 1
	}
	return &Runner{
		WorkspaceMgr: wsMgr,
		concurrency:  concurrency,
		Mode:         ModeLocal,
	}
}

func (r *Runner) SetMode(mode RunnerMode) {
	r.Mode = mode
}

func (r *Runner) SetDB(database *db.DB) {
	r.db = database
}

func (r *Runner) SetExperimentID(id int64) {
	r.experimentID = id
}

func (r *Runner) SetStorage(s storage.Storage) {
	r.Storage = s
}

// RunExperiment starts the orchestration of an experiment.
// In Server mode, it dispatches Cloud Run Jobs.
func (r *Runner) RunExperiment(ctx context.Context, cfg *config.Configuration, experimentID int64) error {
	r.experimentID = experimentID

	// Create Results Channel
	resultsChan := make(chan Result)
	var wg sync.WaitGroup

	// Semaphore for concurrency control
	sem := make(chan struct{}, r.concurrency)

	rc := &runContext{
		Ctx:            ctx,
		ExperimentDir:  "",               // Not used in Server mode
		Timeout:        10 * time.Minute, // Default, should be parsed from cfg
		Timestamp:      time.Now(),
		ExperimentName: cfg.Name,
		ResultsChan:    resultsChan,
		Wg:             &wg,
		Sem:            sem,
	}

	// Parse Timeout from config
	if cfg.Timeout != "" {
		if d, err := time.ParseDuration(cfg.Timeout); err == nil {
			rc.Timeout = d
		}
	}

	log.Printf("[Orchestrator] Starting experiment %d (%s) with %d alternatives", experimentID, cfg.Name, len(cfg.Alternatives))

	// Start Results Listener
	go func() {
		for res := range resultsChan {
			log.Printf("[Orchestrator] Run %d completed: %s", res.RunID, res.Reason)
		}
	}()

	// Dispatch All Jobs
	r.DispatchAll(rc, cfg)

	// Wait for all jobs to be TRIGGERED and monitored
	go func() {
		wg.Wait()
		close(resultsChan)
		log.Printf("[Orchestrator] Experiment %d finished all jobs", experimentID)

		// Final update to Experiment Status
		if r.db != nil {
			_ = r.db.UpdateExperimentStatus(experimentID, "COMPLETED")
		}
	}()

	return nil
}

func (r *Runner) FromDBRunResult(rr *models.RunResult) Result {
	res := Result{
		RunID:            rr.ID,
		Alternative:      rr.Alternative,
		Scenario:         rr.Scenario,
		Repetition:       rr.Repetition,
		Status:           rr.Status,
		Reason:           rr.Reason,
		Duration:         time.Duration(rr.Duration),
		ErrorStr:         rr.Error,
		IsSuccess:        rr.IsSuccess,
		ValidationReport: rr.ValidationReport,
		AgentMetrics: &parser.AgentMetrics{
			TotalTokens:         rr.TotalTokens,
			InputTokens:         rr.InputTokens,
			OutputTokens:        rr.OutputTokens,
			CachedTokens:        rr.CachedTokens,
			TotalToolCallsCount: rr.ToolCallsCount,
			FailedToolCalls:     rr.FailedToolCalls,
		},
		EvaluationMetrics: &models.EvaluationMetrics{
			TestsPassed: rr.TestsPassed,
			TestsFailed: rr.TestsFailed,
			LintIssues:  rr.LintIssues,
		},
	}
	return res
}

func (r *Runner) checkAction() string {

	if r.db == nil || r.experimentID == 0 {
		return ""
	}
	exp, err := r.db.GetExperimentByID(r.experimentID)
	if err != nil {
		return ""
	}
	return exp.ExecutionControl
}

func (r *Result) IsTimeout() bool {
	return r.Reason == db.ReasonFailedTimeout
}

// DetermineRunStatus calculates the final status and reason based on result fields
func (r *Runner) DetermineRunStatus(res *Result) (string, string) {
	status := db.RunStatusCompleted
	reason := db.ReasonSuccess

	if res.ErrorStr != "" {
		if strings.Contains(res.ErrorStr, "deadline exceeded") || strings.Contains(res.ErrorStr, "timeout") {
			reason = db.ReasonFailedTimeout
		} else {
			reason = db.ReasonFailedError
		}
	} else if res.AgentMetrics != nil && res.AgentMetrics.LoopDetected {
		reason = db.ReasonFailedLoop
	} else if !res.IsSuccess && res.ValidationReport != "" {
		reason = db.ReasonFailedValidation
	}

	return status, reason
}
