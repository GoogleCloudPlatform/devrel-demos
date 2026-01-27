package runner

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func (r *Runner) prepareWorkspaceForRun(experimentDir string, alt config.Alternative, scenarioID string, rep int) (*workspace.WorkspaceInfo, error) {
	opts := workspace.WorkspaceOptions{
		Command:          alt.Command,
		SettingsPath:     alt.SettingsPath,
		Settings:         alt.Settings,
		SettingsBlocks:   alt.SettingsBlocks,
		ContextPath:      alt.ContextFilePath,
		Context:          alt.Context,
		SystemPromptPath: alt.SystemPromptFile,
		SystemPrompt:     alt.SystemPrompt,
		PolicyFiles:      alt.PolicyFiles,
		Extensions:       alt.Extensions,
		Skills:           alt.Skills,
		MCPServers:       alt.MCPServers,
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
