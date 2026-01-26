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

	// Enforce required flags for Headless Mode
	hasJSONFormat := false
	hasYolo := false

	for _, arg := range cmdArgs {
		if strings.Contains(arg, "stream-json") {
			hasJSONFormat = true
		}
		if arg == "-y" || arg == "--yolo" {
			hasYolo = true
		}
	}

	if !hasJSONFormat {
		log.Printf("[Runner] Warning: --output-format=stream-json not found in args for %s. Forcing it.", alt.Name)
		cmdArgs = append(cmdArgs, "--output-format=stream-json")
	}

	if !hasYolo {
		log.Printf("[Runner] Warning: --yolo/-y not found in args for %s. Forcing it to ensure non-interactive mode.", alt.Name)
		cmdArgs = append(cmdArgs, "--yolo")
	}

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
	cmd.Env = mergeEnv(os.Environ(), map[string]string{
		"HOME": wsInfo.Home,
	})

	// Prepend project/bin to PATH to allow using locally installed tools (like golangci-lint)
	projectBin := filepath.Join(wsInfo.Project, "bin")
	currentPath := os.Getenv("PATH")
	newPath := fmt.Sprintf("%s%c%s", projectBin, os.PathListSeparator, currentPath)
	cmd.Env = mergeEnv(cmd.Env, map[string]string{
		"PATH": newPath,
	})

	// Add alt.Env
	cmd.Env = mergeEnv(cmd.Env, alt.Env)

	// Add System Prompt
	systemPath := filepath.Join(wsInfo.Project, "SYSTEM.md")
	if _, err := os.Stat(systemPath); err == nil {
		cmd.Env = mergeEnv(cmd.Env, map[string]string{
			"GEMINI_SYSTEM_MD": systemPath,
		})
	}

	// Share Go caches
	goEnv := make(map[string]string)

	// Try to get them from go env if not in current env
	goEnvCmd := exec.Command("go", "env", "GOCACHE", "GOMODCACHE")
	goEnvOut, err := goEnvCmd.Output()
	if err == nil {
		parts := strings.Split(strings.TrimSpace(string(goEnvOut)), "\n")
		if len(parts) >= 2 {
			goEnv["GOCACHE"] = parts[0]
			goEnv["GOMODCACHE"] = parts[1]
		}
	}
	cmd.Env = mergeEnv(cmd.Env, goEnv)

	return cmd, jobCtx, jobCancel, execCtx, execCancel, nil
}

// mergeEnv merges new key-value pairs into an existing environment slice.
// It overrides existing keys and appends new ones, preventing duplicates.
func mergeEnv(base []string, overrides map[string]string) []string {
	// Parse base into a map for easy lookup
	envMap := make(map[string]string)
	for _, entry := range base {
		parts := strings.SplitN(entry, "=", 2)
		if len(parts) == 2 {
			envMap[parts[0]] = parts[1]
		}
	}

	// Apply overrides
	for k, v := range overrides {
		envMap[k] = v
	}

	// Reconstruct slice
	result := make([]string, 0, len(envMap))
	for k, v := range envMap {
		result = append(result, fmt.Sprintf("%s=%s", k, v))
	}
	return result
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
