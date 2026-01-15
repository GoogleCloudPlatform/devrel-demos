package runner

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/parser"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func (r *Runner) prepareWorkspaceForRun(experimentDir string, alt config.Alternative, scenarioID string, rep int) (*workspace.WorkspaceInfo, error) {
	// Ensure paths are absolute before passing to WorkspaceMgr
	opts := workspace.WorkspaceOptions{
		SettingsPath:     alt.SettingsPath,
		Settings:         alt.Settings,
		ContextPath:      alt.ContextFilePath,
		Context:          alt.Context,
		SystemPromptPath: alt.SystemPromptFile,
		SystemPrompt:     alt.SystemPrompt,
		PolicyFiles:      alt.PolicyFiles,
	}

	if opts.SettingsPath != "" {
		if abs, err := filepath.Abs(opts.SettingsPath); err == nil {
			opts.SettingsPath = abs
		}
	}
	if opts.ContextPath != "" {
		if abs, err := filepath.Abs(opts.ContextPath); err == nil {
			opts.ContextPath = abs
		}
	}
	if opts.SystemPromptPath != "" {
		if abs, err := filepath.Abs(opts.SystemPromptPath); err == nil {
			opts.SystemPromptPath = abs
		}
	}
	info, err := r.WorkspaceMgr.PrepareWorkspace(experimentDir, alt.Name, scenarioID, rep, opts)
	if err != nil {
		return nil, err
	}
	return &info, nil
}

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

	// Collect Host Env
	hostEnv := make(map[string]string)
	for _, e := range os.Environ() {
		parts := strings.SplitN(e, "=", 2)
		if len(parts) == 2 {
			hostEnv[parts[0]] = parts[1]
		}
	}

	// 1. Scenario Level Env
	if wsInfo.Config != nil {
		for k, v := range wsInfo.Config.Env {
			val := v
			if strings.HasPrefix(v, "$") {
				val = hostEnv[strings.TrimPrefix(v, "$")]
			}
			envMap[k] = val
		}
	}

	// 2. Alternative Level Env (Overrides Scenario)
	for k, v := range alt.Env {
		val := v
		if strings.HasPrefix(v, "$") {
			val = hostEnv[strings.TrimPrefix(v, "$")]
		}
		envMap[k] = val
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

func (r *Runner) streamPromptContents(promptPath string, stdinPipe io.WriteCloser) {
	defer stdinPipe.Close() // Ensure EOF is sent
	// Open the prompt file here to ensure we have a fresh handle
	promptFile, err := os.Open(promptPath)
	if err != nil {
		log.Printf("Warning: failed to open PROMPT.md for streaming: %v", err)
		return
	}
	defer promptFile.Close()

	if _, err := io.Copy(stdinPipe, promptFile); err != nil {
		log.Printf("Warning: failed to copy prompt to stdin: %v", err)
		return
	}

	// Inject termination instruction
	instruction := "\n\nSYSTEM: Perform the requested task above. When you have FULLY completed the user request (including all verification steps), you MUST output the token '<<TENKAI_DONE>>' to signal completion. Do not output this token before the work is done. IMPORTANT: Do not delete any files or directories you created. They are needed for automated validation.\n"
	if _, err := io.WriteString(stdinPipe, instruction); err != nil {
		log.Printf("Warning: failed to write termination instruction to stdin: %v", err)
	}
}

func (r *Runner) streamStdout(stdoutPipe io.ReadCloser, logFile io.Writer, jobID string, res *Result, cmd *exec.Cmd, streamWg *sync.WaitGroup, stdoutMu *sync.Mutex, currentStdout *strings.Builder, terminationRequested *bool, resultFound *bool, resultFoundMu *sync.Mutex, execCancel context.CancelFunc) {
	defer streamWg.Done()
	scanner := bufio.NewScanner(stdoutPipe)

	// Ensure metrics struct exists on the result
	if res.AgentMetrics == nil {
		res.AgentMetrics = &parser.AgentMetrics{}
	}
	metrics := res.AgentMetrics

	pendingTools := make(map[string]*parser.ToolCall)
	var lastToolCount int
	var resultSaved bool

	for scanner.Scan() {
		line := scanner.Text()
		fmt.Fprintln(logFile, line)

		stdoutMu.Lock()
		currentStdout.WriteString(line + "\n")
		stdoutMu.Unlock()

		// Real-time parsing and event emission
		evt, err := parser.ParseLine(line, metrics, pendingTools)
		if err != nil && errors.Is(err, parser.ErrTerminationRequested) {
			// Termination requested by agent
			log.Printf("[Runner] Termination token detected for %s. Requesting graceful shutdown.", jobID)

			*terminationRequested = true

			// TRIGGER GRACEFUL SHUTDOWN (Delayed)
			go func() {
				time.Sleep(2 * time.Second)
				if cmd.Process != nil {
					if err := cmd.Process.Signal(os.Interrupt); err != nil {
						log.Printf("[Runner] Failed to send SIGINT to %s: %v", jobID, err)
					}
				}
			}()
		}

		if evt != nil {
			if res.RunID != 0 {
				// Check for new tool results
				if len(metrics.ToolCalls) > lastToolCount {
					newTools := metrics.ToolCalls[lastToolCount:]
					for _, tc := range newTools {
						r.db.SaveRunEvent(res.RunID, "tool", tc)
					}
					lastToolCount = len(metrics.ToolCalls)
				}
				// Save EVERY raw event to the database immediately.
				r.db.SaveRunEvent(res.RunID, evt.Type, evt)
			}
			// Check for final result stats (Early Exit)
			if !resultSaved && metrics.Result != "" {
				resultSaved = true
				log.Printf("[Runner] Result detected for %s. Triggering early exit.", jobID)

				resultFoundMu.Lock()
				*resultFound = true
				resultFoundMu.Unlock()

				execCancel()
			}
		}
	}
}

func (r *Runner) streamStderr(stderrPipe io.ReadCloser, stderrFile io.Writer, res *Result, streamWg *sync.WaitGroup, stderrMu *sync.Mutex, currentStderr *strings.Builder) {
	defer streamWg.Done()
	scanner := bufio.NewScanner(stderrPipe)
	for scanner.Scan() {
		line := scanner.Text()
		fmt.Fprintln(stderrFile, line)

		stderrMu.Lock()
		currentStderr.WriteString(line + "\n")
		stderrMu.Unlock()

		if res.RunID != 0 && strings.TrimSpace(line) != "" {
			now := time.Now()
			errEvt := &parser.GeminiEvent{
				Type:      "error",
				Timestamp: now.Format(time.RFC3339),
				Severity:  "error",
				Message:   line,
			}
			r.db.SaveRunEvent(res.RunID, "error", errEvt)
		}
	}
}

func (r *Runner) syncLogs(ctx context.Context, res *Result, stdoutMu *sync.Mutex, currentStdout *strings.Builder, stderrMu *sync.Mutex, currentStderr *strings.Builder) {
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			stdoutMu.Lock()
			out := currentStdout.String()
			stdoutMu.Unlock()
			stderrMu.Lock()
			errStr := currentStderr.String()
			stderrMu.Unlock()
			r.db.UpdateRunLogs(res.RunID, out, errStr)
		}
	}
}
func (r *Runner) setupLogFiles(wsInfo *workspace.WorkspaceInfo, altName, scenarioID string, rep int) (*os.File, *os.File, string, error) {
	safeAlt := strings.ReplaceAll(altName, " ", "_")
	safeScen := strings.ReplaceAll(scenarioID, " ", "_")
	logFilename := fmt.Sprintf("%s_%s_rep%d", safeAlt, safeScen, rep)

	logPath := filepath.Join(wsInfo.Logs, logFilename+".jsonl")
	logFile, err := os.Create(logPath)
	if err != nil {
		return nil, nil, "", fmt.Errorf("failed to create events log: %w", err)
	}

	stderrPath := filepath.Join(wsInfo.Logs, logFilename+".stderr.log")
	stderrFile, err := os.Create(stderrPath)
	if err != nil {
		logFile.Close()
		return nil, nil, "", fmt.Errorf("failed to create stderr log: %w", err)
	}

	return logFile, stderrFile, logPath, nil
}

func (r *Runner) waitForCommand(cmd *exec.Cmd, streamWg *sync.WaitGroup, jobCtx context.Context, timeout time.Duration, jobID string, resultFound *bool, resultFoundMu *sync.Mutex, terminationRequested *bool) error {
	// Wait for streams to finish (pipes closed)
	streamWg.Wait()

	if err := cmd.Wait(); err != nil {
		// Check if early exit triggered
		resultFoundMu.Lock()
		isEarlyExit := *resultFound
		resultFoundMu.Unlock()

		startGracefulExit := *terminationRequested

		if isEarlyExit {
			// Ignore error, treat as success (result already captured)
			return nil
		} else if startGracefulExit {
			// Agent requested termination via token.
			// Treat as success even if the process was killed with SIGINT.
			// However, we must ensure we actually parsed the result.
			log.Printf("[Runner] Process %s exited locally after termination token: %v", jobID, err)
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
