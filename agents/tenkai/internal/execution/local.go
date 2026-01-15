package execution

import (
	"context"
	"fmt"
	"io"
	"os/exec"
	"syscall"
)

// LocalExecutor implements Executor for local process execution.
type LocalExecutor struct{}

func NewLocalExecutor() *LocalExecutor {
	return &LocalExecutor{}
}

func (e *LocalExecutor) Execute(ctx context.Context, cfg JobConfig, stdin io.Reader, stdout, stderr io.Writer) ExecutionResult {
	if len(cfg.Command) == 0 {
		return ExecutionResult{ExitCode: 1, Error: fmt.Errorf("empty command")}
	}

	cmd := exec.CommandContext(ctx, cfg.Command[0], cfg.Command[1:]...)
	cmd.Dir = cfg.WorkDir
	cmd.Stdin = stdin

	// Prepare Env
	cmd.Env = []string{}
	// Inherit PATH and other basics? Or full isolation?
	// Tenkai usually creates a full env map.
	for k, v := range cfg.Env {
		cmd.Env = append(cmd.Env, fmt.Sprintf("%s=%s", k, v))
	}

	cmd.Stdout = stdout
	cmd.Stderr = stderr

	// Process Group to ensure we can kill children (runner logic)
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	cmd.Cancel = func() error {
		if cmd.Process != nil {
			return syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
		}
		return nil
	}

	if err := cmd.Start(); err != nil {
		return ExecutionResult{ExitCode: 126, Error: fmt.Errorf("failed to start: %w", err)}
	}

	err := cmd.Wait()
	res := ExecutionResult{}

	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			res.ExitCode = exitErr.ExitCode()
			res.Error = nil // ExitError is "normal" execution failure, not system error?
			// Actually Tenkai logic treats non-zero exit as potential validation failure,
			// but here we just report what happened.
			// Let's propagate the error if non-zero, but storing exit code is key.
		} else {
			res.ExitCode = 1
			res.Error = err
		}
	} else {
		res.ExitCode = 0
	}

	return res
}
