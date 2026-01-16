package workspace

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
)

// WorkspaceInfo contains the paths for a prepared workspace.
type WorkspaceInfo struct {
	Root    string
	Project string
	Home    string
	Logs    string
	Config  *config.ScenarioConfig // Passed in-memory to avoid reloading from disk
}

// WorkspaceOptions defines the configuration for a workspace.
type WorkspaceOptions struct {
	SettingsPath     string
	Settings         map[string]interface{}
	ContextPath      string
	Context          string
	SystemPromptPath string
	SystemPrompt     string
	PolicyFiles      []string
}

// PrepareWorkspace creates an isolated workspace for a specific run.
// Structure: <experimentDir>/<alternative>/<scenario>/<repetition>/{project,home,logs}
func (m *Manager) PrepareWorkspace(experimentDir, alternative, scenario string, repetition int, opts WorkspaceOptions) (WorkspaceInfo, error) {
	baseWSPath := filepath.Join(experimentDir, alternative, scenario, fmt.Sprintf("rep-%d", repetition))
	wsPath := baseWSPath

	// Checking for existing directory and finding a unique suffix
	counter := 1
	for {
		if _, err := os.Stat(wsPath); os.IsNotExist(err) {
			break
		}
		wsPath = fmt.Sprintf("%s_relaunch_%d", baseWSPath, counter)
		counter++
	}

	info := WorkspaceInfo{
		Root:    wsPath,
		Project: filepath.Join(wsPath, "project"),
		Home:    filepath.Join(wsPath, "home"),
		Logs:    filepath.Join(wsPath, "logs"),
	}

	dirs := []string{info.Project, info.Home, info.Logs}
	for _, d := range dirs {
		if err := os.MkdirAll(d, 0755); err != nil {
			return info, fmt.Errorf("failed to create directory %s: %w", d, err)
		}
	}

	// Copy template content to project dir
	var tmplPath string
	for _, dir := range m.TemplatesDirs {
		path := filepath.Join(dir, scenario)
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			tmplPath = path
			break
		}
	}

	if tmplPath == "" {
		return info, fmt.Errorf("scenario template %q not found in any of: %v", scenario, m.TemplatesDirs)
	}
	// Check for scenario.yaml
	scenarioConfigPath := filepath.Join(tmplPath, "scenario.yaml")
	if _, err := os.Stat(scenarioConfigPath); err == nil {
		scenCfg, err := config.LoadScenarioConfig(scenarioConfigPath)
		if err != nil {
			return info, fmt.Errorf("failed to load scenario config: %w", err)
		}
		info.Config = scenCfg

		// Process Assets into project dir
		if err := m.SyncAssets(scenCfg, tmplPath, info.Project); err != nil {
			return info, fmt.Errorf("failed to sync assets: %w", err)
		}

		// Generate PROMPT.md in project dir
		promptContent := scenCfg.Task
		if scenCfg.GithubIssue != "" {
			issueContent, err := fetchGithubIssue(scenCfg.GithubIssue)
			if err != nil {
				promptContent += fmt.Sprintf("\n\n(Failed to fetch issue context: %v)", err)
			} else {
				promptContent = fmt.Sprintf("# Task from GitHub Issue: %s\n\n**Title**: %s\n\n**Description**:\n%s\n\n%s",
					scenCfg.GithubIssue, issueContent.Title, issueContent.Body, promptContent)
			}
		}
		if promptContent != "" {
			if err := os.WriteFile(filepath.Join(info.Project, "PROMPT.md"), []byte(promptContent), 0644); err != nil {
				return info, fmt.Errorf("failed to write PROMPT.md: %w", err)
			}
		}

	} else {
		return info, fmt.Errorf("scenario.yaml not found in %s", tmplPath)
	}

	// Handle Tool settings in project/.gemini
	geminiDir := filepath.Join(info.Project, ".gemini")
	if opts.SettingsPath != "" || len(opts.Settings) > 0 {
		if err := os.MkdirAll(geminiDir, 0755); err != nil {
			return info, fmt.Errorf("failed to create .gemini directory: %w", err)
		}
		destSettings := filepath.Join(geminiDir, "settings.json")
		if opts.SettingsPath != "" {
			if err := copyFile(opts.SettingsPath, destSettings); err != nil {
				return info, fmt.Errorf("failed to create settings file: %w", err)
			}
		} else {
			f, err := os.Create(destSettings)
			if err != nil {
				return info, fmt.Errorf("failed to create settings file: %w", err)
			}
			enc := json.NewEncoder(f)
			enc.SetIndent("", "  ")
			if err := enc.Encode(opts.Settings); err != nil {
				f.Close()
				return info, fmt.Errorf("failed to encode settings: %w", err)
			}
			f.Close()
		}
	}

	// Handle Context File (GEMINI.md) in project dir
	if opts.ContextPath != "" || opts.Context != "" {
		destContext := filepath.Join(info.Project, "GEMINI.md")
		if opts.ContextPath != "" {
			if err := copyFile(opts.ContextPath, destContext); err != nil {
				return info, fmt.Errorf("failed to copy context file: %w", err)
			}
		} else {
			if err := os.WriteFile(destContext, []byte(opts.Context), 0644); err != nil {
				return info, fmt.Errorf("failed to write context file: %w", err)
			}
		}
	}

	// Handle System Prompt File (SYSTEM.md) in project dir
	if opts.SystemPromptPath != "" || opts.SystemPrompt != "" {
		destSystem := filepath.Join(info.Project, "SYSTEM.md")
		if opts.SystemPromptPath != "" {
			if err := copyFile(opts.SystemPromptPath, destSystem); err != nil {
				return info, fmt.Errorf("failed to copy system prompt file: %w", err)
			}
		} else {
			if err := os.WriteFile(destSystem, []byte(opts.SystemPrompt), 0644); err != nil {
				return info, fmt.Errorf("failed to write system prompt file: %w", err)
			}
		}
	}

	// Handle Policy Files in project/.gemini/policies
	if len(opts.PolicyFiles) > 0 {
		policiesDir := filepath.Join(geminiDir, "policies")
		if err := os.MkdirAll(policiesDir, 0755); err != nil {
			return info, fmt.Errorf("failed to create policies directory: %w", err)
		}

		for _, pf := range opts.PolicyFiles {
			destPolicy := filepath.Join(policiesDir, filepath.Base(pf))
			if err := copyFile(pf, destPolicy); err != nil {
				return info, fmt.Errorf("failed to copy policy file %s: %w", pf, err)
			}
		}
	}

	return info, nil
}
