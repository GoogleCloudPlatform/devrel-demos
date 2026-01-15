package execution

import (
	"context"
	"fmt"
	"io"
	"os"

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

	// Name format: projects/{project}/locations/{location}/jobs/{job}
	// We use TENKAI_JOB_NAME env var, constructed by the deploy script/server environment.
	// Fallback to strict format if needed.
	jobName := os.Getenv("TENKAI_JOB_NAME")
	if jobName == "" {
		// Try to construct from components if available
		project := os.Getenv("GOOGLE_CLOUD_PROJECT")
		region := os.Getenv("TENKAI_REGION")
		if project != "" && region != "" {
			jobName = fmt.Sprintf("projects/%s/locations/%s/jobs/tenkai-worker", project, region)
		}
	}

	if jobName == "" {
		return ExecutionResult{ExitCode: 1, Error: fmt.Errorf("Cloud Run Job name (TENKAI_JOB_NAME) is required")}
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
			Values: &runpb.EnvVar_Value{
				Value: v,
			},
		})
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
