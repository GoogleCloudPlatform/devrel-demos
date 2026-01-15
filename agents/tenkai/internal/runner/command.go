package runner

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func (r *Runner) createCommand(ctx context.Context, alt config.Alternative, wsInfo *workspace.WorkspaceInfo, timeout time.Duration, jobID string) (*exec.Cmd, context.Context, context.CancelFunc, context.Context, context.CancelFunc, error) {
	// Create timeout context for the entire job (run + verification)
	jobCtx, jobCancel := context.WithTimeout(ctx, timeout)

	// Execution Context (Can be cancelled early without killing validation)
	execCtx, execCancel := context.WithCancel(jobCtx)

	cmdName := alt.Command
	cmdArgs := make([]string, len(alt.Args))
	copy(cmdArgs, alt.Args)

	cmd := exec.CommandContext(execCtx, cmdName, cmdArgs...)
	cmd.Dir = wsInfo.Project

	// Create a new Process Group to handle orphan cleanup
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	// Ensure that on context cancellation (timeout or abort), we kill the whole process group
	cmd.Cancel = func() error {
		if cmd.Process != nil {
			log.Printf("[Runner] Kill signal triggered for %s (PID %d)", jobID, cmd.Process.Pid)
			// Kill the process group by passing negative PID (works because Setpgid: true)
			return syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
		}
		return nil
	}

	cmd.WaitDelay = 2 * time.Second

	// Environment setup
	cmd.Env = os.Environ()
	cmd.Env = append(cmd.Env, fmt.Sprintf("HOME=%s", wsInfo.Home))

	envMap := make(map[string]string)
	for k, v := range alt.Env {
		envMap[k] = v
	}

	systemPath := filepath.Join(wsInfo.Project, "SYSTEM.md")
	if _, err := os.Stat(systemPath); err == nil {
		envMap["GEMINI_SYSTEM_MD"] = systemPath
	}

	for k, v := range envMap {
		cmd.Env = append(cmd.Env, fmt.Sprintf("%s=%s", k, v))
	}

	// Share Go caches
	if goCache := os.Getenv("GOCACHE"); goCache != "" {
		cmd.Env = append(cmd.Env, fmt.Sprintf("GOCACHE=%s", goCache))
	}

	goEnvCmd := exec.Command("go", "env", "GOCACHE", "GOMODCACHE")
	goEnvOut, err := goEnvCmd.Output()
	if err == nil {
		parts := strings.Split(strings.TrimSpace(string(goEnvOut)), "\n")
		if len(parts) >= 2 {
			cmd.Env = append(cmd.Env, fmt.Sprintf("GOCACHE=%s", parts[0]))
			cmd.Env = append(cmd.Env, fmt.Sprintf("GOMODCACHE=%s", parts[1]))
		}
	}

	return cmd, jobCtx, jobCancel, execCtx, execCancel, nil
}

func (r *Runner) waitForCommand(cmd *exec.Cmd, s *StreamState, jobCtx context.Context, timeout time.Duration) error {
	// Wait for streams to finish (pipes closed)
	s.StreamWg.Wait()

	if err := cmd.Wait(); err != nil {
		// Check if early exit triggered
		isEarlyExit := s.IsResultFound()
		startGracefulExit := s.IsTerminationRequested()

		if isEarlyExit {
			// Ignore error, treat as success (result already captured)
			return nil
		} else if startGracefulExit {
			// Agent requested termination via token.
			// Treat as success even if the process was killed with SIGINT.
			log.Printf("[Runner] Process %s exited locally after termination token: %v", s.JobID, err)
			return nil
		} else if jobCtx.Err() == context.DeadlineExceeded {
			// Check if timeout
			return fmt.Errorf("execution timeout (%v limit)", timeout)
		} else {
			return fmt.Errorf("execution failed: %w", err)
		}
	}
	return nil
}
