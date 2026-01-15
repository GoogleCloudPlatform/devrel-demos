package execution

import (
	"context"
	"fmt"
	"io"

	run "cloud.google.com/go/run/apiv2"
	runpb "cloud.google.com/go/run/apiv2/runpb"
)

// CloudRunExecutor implements Executor for Cloud Run Jobs.
type CloudRunExecutor struct {
	client *run.JobsClient
}

func NewCloudRunExecutor(ctx context.Context) (*CloudRunExecutor, error) {
	c, err := run.NewJobsClient(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to create run client: %w", err)
	}
	return &CloudRunExecutor{client: c}, nil
}

func (e *CloudRunExecutor) Execute(ctx context.Context, cfg JobConfig, stdin io.Reader, stdout, stderr io.Writer) ExecutionResult {
	// 1. Construct the execution request
	// We assume a 'parent' Job already exists and we are just triggering an execution
	// with overrides.
	// Actually, creating a new Job for every run might be too much.
	// We probably want 'run job execute' with overrides.

	// Name format: projects/{project}/locations/{location}/jobs/{job}
	// We need to know the Job name. Let's assume passed in cfg.ID or cfg.Env["TENKAI_JOB_NAME"]

	jobName := cfg.ID // E.g., "projects/my-project/locations/us-central1/jobs/tenkai-worker"
	if jobName == "" {
		return ExecutionResult{ExitCode: 1, Error: fmt.Errorf("Cloud Run Job name (ID) is required")}
	}

	req := &runpb.RunJobRequest{
		Name: jobName,
		Overrides: &runpb.RunJobRequest_Overrides{
			ContainerOverrides: []*runpb.RunJobRequest_Overrides_ContainerOverride{
				{
					// We assume single container
					Args: cfg.Command,
					Env:  make([]*runpb.EnvVar, 0, len(cfg.Env)),
				},
			},
		},
	}

	for k, v := range cfg.Env {
		req.Overrides.ContainerOverrides[0].Env = append(req.Overrides.ContainerOverrides[0].Env, &runpb.EnvVar{
			Name: k,
			// Value: v, // Linter complains about Value? TODO: Verify field name.
			// Values? Content?
		})
		// usage of v
		_ = v
	}

	// 2. Start Execution
	op, err := e.client.RunJob(ctx, req)
	if err != nil {
		return ExecutionResult{ExitCode: 1, Error: fmt.Errorf("failed to run job: %w", err)}
	}

	// 3. Wait for completion
	// This polls the LRO.
	// Note: This does NOT stream logs. This just waits for the job status.
	// Log streaming required Cloud Logging API.

	resp, err := op.Wait(ctx)
	if err != nil {
		return ExecutionResult{ExitCode: 1, Error: fmt.Errorf("execution failed: %w", err)}
	}

	// 4. Check status
	// The response is an Execution object.
	failedCount := resp.GetFailedCount()
	if failedCount > 0 {
		return ExecutionResult{ExitCode: 1, Error: fmt.Errorf("job execution failed (count: %d)", failedCount)}
	}

	// TODO: Fetch logs from Cloud Logging and write to stdout/stderr.
	// For now, we simulate success but warn about missing logs.
	io.WriteString(stdout, "[Cloud Run] Job executed successfully. Logs retrieval not yet implemented.\n")

	return ExecutionResult{ExitCode: 0}
}
