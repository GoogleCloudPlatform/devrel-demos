package execution

import (
	"context"
	"io"
)

// JobConfig defines the parameters for a job execution.
type JobConfig struct {
	ID             string            // Unique Job ID
	Image          string            // Container image (for Cloud Run) or irrelevant for Local
	Command        []string          // Command to run
	Env            map[string]string // Environment variables
	WorkDir        string            // Working directory
	ProjectID      string            // GCP Project ID (for Cloud Run)
	Region         string            // GCP Region (for Cloud Run)
	ServiceAccount string            // Service Account (for Cloud Run)
}

// ExecutionResult represents the outcome of an execution.
type ExecutionResult struct {
	ExitCode int
	Error    error
}

// Executor abstracts the execution environment.
type Executor interface {
	// Execute runs the job and returns a way to stream logs/wait.
	// This is a blocking call that waits for the job to complete or context cancel.
	Execute(ctx context.Context, cfg JobConfig, stdin io.Reader, stdout, stderr io.Writer) ExecutionResult
}
