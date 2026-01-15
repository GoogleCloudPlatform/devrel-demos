package runner

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/execution"
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

func (r *Runner) createJobConfig(ctx context.Context, alt config.Alternative, wsInfo *workspace.WorkspaceInfo, timeout time.Duration, jobID string) (execution.JobConfig, context.Context, context.CancelFunc, context.Context, context.CancelFunc, error) {
	// Create timeout context for the entire job (run + verification)
	jobCtx, jobCancel := context.WithTimeout(ctx, timeout)

	// Execution Context (Can be cancelled early without killing validation)
	execCtx, execCancel := context.WithCancel(jobCtx)

	cmdName := alt.Command
	cmdArgs := make([]string, len(alt.Args))
	copy(cmdArgs, alt.Args)

	// Prepare JobConfig
	cfg := execution.JobConfig{
		ID:      jobID,
		Command: append([]string{cmdName}, cmdArgs...),
		WorkDir: wsInfo.Project,
		Env:     make(map[string]string),
	}

	// Environment setup
	// 1. Host Env
	hostEnv := make(map[string]string)
	for _, e := range os.Environ() {
		parts := strings.SplitN(e, "=", 2)
		if len(parts) == 2 {
			cfg.Env[parts[0]] = parts[1]
			hostEnv[parts[0]] = parts[1]
		}
	}
	// Always force HOME
	cfg.Env["HOME"] = wsInfo.Home

	// 2. Scenario Level Env
	if wsInfo.Config != nil {
		for k, v := range wsInfo.Config.Env {
			val := v
			if strings.HasPrefix(v, "$") {
				val = hostEnv[strings.TrimPrefix(v, "$")]
			}
			cfg.Env[k] = val
		}
	}

	// 3. Alternative Level Env (Overrides Scenario)
	for k, v := range alt.Env {
		val := v
		if strings.HasPrefix(v, "$") {
			val = hostEnv[strings.TrimPrefix(v, "$")]
		}
		cfg.Env[k] = val
	}

	systemPath := filepath.Join(wsInfo.Project, "SYSTEM.md")
	if _, err := os.Stat(systemPath); err == nil {
		cfg.Env["GEMINI_SYSTEM_MD"] = systemPath
	}

	// Share Go caches
	if goCache := os.Getenv("GOCACHE"); goCache != "" {
		cfg.Env["GOCACHE"] = goCache
	}

	goEnvCmd := exec.Command("go", "env", "GOCACHE", "GOMODCACHE")
	goEnvOut, err := goEnvCmd.Output()
	if err == nil {
		parts := strings.Split(strings.TrimSpace(string(goEnvOut)), "\n")
		if len(parts) >= 2 {
			cfg.Env["GOCACHE"] = parts[0]
			cfg.Env["GOMODCACHE"] = parts[1]
		}
	}

	return cfg, jobCtx, jobCancel, execCtx, execCancel, nil
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
