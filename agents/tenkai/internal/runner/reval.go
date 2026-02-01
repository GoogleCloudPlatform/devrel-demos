package runner

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/jobs"
)

// ReEvaluateExperiment runs validation again for all completed runs in an experiment
func (r *Runner) ReEvaluateExperiment(expID int64, jobID string) error {
	jobMgr := jobs.GetManager()

	runs, err := r.db.GetRunResults(expID, 10000, 0)
	if err != nil {
		jobMgr.FailJob(jobID, err)
		return fmt.Errorf("failed to fetch runs: %w", err)
	}

	// Filter runs to re-evaluate
	var pendingRuns []models.RunResult
	for _, run := range runs {
		if run.Reason == db.ReasonFailedValidation {
			pendingRuns = append(pendingRuns, run)
		}
	}

	jobMgr.UpdateProgress(jobID, 0, len(pendingRuns))

	// Fetch Experiment to find Dir
	exp, err := r.db.GetExperimentByID(expID)
	if err != nil {
		jobMgr.FailJob(jobID, err)
		return fmt.Errorf("failed to fetch experiment: %w", err)
	}

	expDir, err := r.WorkspaceMgr.FindExperimentDir(exp.Timestamp, exp.Name)
	if err != nil {
		jobMgr.FailJob(jobID, err)
		return fmt.Errorf("failed to locate experiment directory: %w", err)
	}
	// Assuming scenarios are in standard location
	cwd, _ := os.Getwd()
	templatesDir := filepath.Join(cwd, "scenarios")

	log.Printf("Re-evaluating %d runs for experiment %d", len(pendingRuns), expID)

	successCount := 0
	for i, run := range pendingRuns {
		if err := r.reEvalInternal(&run, expDir, templatesDir); err != nil {
			log.Printf("Failed to re-evaluate run %d: %v", run.ID, err)
		} else {
			successCount++
		}
		jobMgr.UpdateProgress(jobID, i+1, len(pendingRuns))
	}

	jobMgr.CompleteJob(jobID)
	return nil
}

// ReEvaluateRun runs validation again for a single run
func (r *Runner) ReEvaluateRun(runID int64, jobID string) error {
	jobMgr := jobs.GetManager()
	jobMgr.UpdateProgress(jobID, 0, 1)

	run, err := r.db.GetRunByID(runID)
	if err != nil {
		jobMgr.FailJob(jobID, err)
		return fmt.Errorf("failed to fetch run: %w", err)
	}

	if run.Reason != db.ReasonFailedValidation {
		err := fmt.Errorf("cannot re-validate run with reason %s, only %s is supported", run.Reason, db.ReasonFailedValidation)
		jobMgr.FailJob(jobID, err)
		return err
	}

	exp, err := r.db.GetExperimentByID(run.ExperimentID)
	if err != nil {
		jobMgr.FailJob(jobID, err)
		return fmt.Errorf("failed to fetch experiment: %w", err)
	}

	expDir, err := r.WorkspaceMgr.FindExperimentDir(exp.Timestamp, exp.Name)
	if err != nil {
		jobMgr.FailJob(jobID, err)
		return fmt.Errorf("failed to locate experiment directory: %w", err)
	}
	cwd, _ := os.Getwd()
	templatesDir := filepath.Join(cwd, "scenarios")

	if err := r.reEvalInternal(run, expDir, templatesDir); err != nil {
		jobMgr.FailJob(jobID, err)
		return err
	}

	jobMgr.UpdateProgress(jobID, 1, 1)
	jobMgr.CompleteJob(jobID)
	return nil
}

// Internal implementation of ReEval logic
func (r *Runner) reEvalInternal(run *models.RunResult, expDir, templatesDir string) error {
	log.Printf("Re-evaluating Run %d...", run.ID)

	wsPath := filepath.Join(expDir, run.Alternative, run.Scenario, fmt.Sprintf("rep-%d", run.Repetition))
	if _, err := os.Stat(wsPath); os.IsNotExist(err) {
		// Workspace missing (common in Cloud Run / Distributed mode)
		// Try to restore from Storage to a temporary directory
		if r.Storage != nil {
			tempDir, err := os.MkdirTemp("", fmt.Sprintf("tenkai-reval-%d-*", run.ID))
			if err != nil {
				return fmt.Errorf("creating temp dir for restoration: %w", err)
			}
			// Ideally we defer removal, but for debugging maybe keep?
			// defer os.RemoveAll(tempDir)
			// Let's remove it to save space on Cloud Run
			defer func() { _ = os.RemoveAll(tempDir) }()

			log.Printf("Restoring artifacts for Run %d to %s...", run.ID, tempDir)
			if err := r.Storage.DownloadRunArtifacts(context.Background(), run.ID, tempDir); err != nil {
				return fmt.Errorf("CRITICAL: failed to restore artifacts: %w. Validation cannot proceed.", err)
			}

			// Use the temp dir as the workspace path
			wsPath = tempDir
		} else {
			return fmt.Errorf("CRITICAL: Workspace path not found and no Storage configured: %s", wsPath)
		}
	}
	projectPath := filepath.Join(wsPath, "project")
	// If projectPath doesn't exist (e.g. restoration was partial or empty), create it
	if _, err := os.Stat(projectPath); os.IsNotExist(err) {
		_ = os.MkdirAll(projectPath, 0755)
	}

	// Load Scenario Config
	scenTemplatePath := filepath.Join(templatesDir, run.Scenario, "scenario.yaml")
	scenCfg, err := config.LoadScenarioConfig(scenTemplatePath)
	if err != nil {
		return fmt.Errorf("loading scenario config: %w", err)
	}

	// Sync Assets (Update workspace with latest scenario files)
	// We need the template path to copy from
	if err := r.WorkspaceMgr.SyncAssets(context.Background(), scenCfg, filepath.Dir(scenTemplatePath), projectPath); err != nil {
		return fmt.Errorf("syncing assets: %w", err)
	}

	// Get Stdout
	stdout, err := r.db.GetRunStdout(run.ID)
	if err != nil {
		return fmt.Errorf("fetching stdout: %w", err)
	}

	// Run Validation
	ctx := context.Background()
	metrics, report, err := r.evaluateCode(ctx, projectPath, scenCfg, stdout)
	if err != nil {
		return fmt.Errorf("evaluation failed: %w", err)
	}

	// Update struct using centralized logic
	updatedRun := *run
	r.ApplyValidationReport(&updatedRun, report)
	updatedRun.Status = "COMPLETED"

	// Ensure metrics are applied (evaluateCode handles mapping)
	updatedRun.TestsPassed = metrics.TestsPassed
	updatedRun.TestsFailed = metrics.TestsFailed
	updatedRun.LintIssues = metrics.LintIssues

	telemetry := &db.RunTelemetry{
		Result:      &updatedRun,
		TestResults: report.DetailedTests,
		LintResults: report.DetailedLints,
	}

	if err := r.db.SaveRunTelemetry(telemetry); err != nil {
		return fmt.Errorf("saving result: %w", err)
	} else {
		log.Printf("✅ Updated Run %d: %s", run.ID, updatedRun.Reason)
	}

	return nil
}
