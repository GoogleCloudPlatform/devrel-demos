package workspace

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

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
	Command          string // Command to run 'gemini skills install' (e.g. "gemini")
	SettingsPath     string
	Settings         map[string]interface{}
	SettingsBlocks   []map[string]interface{}
	ContextPath      string
	Context          string
	SystemPromptPath string
	SystemPrompt     string
	PolicyFiles      []string
	Extensions       []config.ExtensionConfig
	Skills           []config.SkillConfig
	MCPServers       []config.MCPConfig
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

	// 1. Initialize Settings if nil
	if opts.Settings == nil {
		opts.Settings = make(map[string]interface{})
	}

	// 2. Merge SettingsBlocks sequentially (Order matters: later blocks override earlier ones)
	finalSettings := make(map[string]interface{})
	for _, block := range opts.SettingsBlocks {
		if err := deepMerge(finalSettings, block); err != nil {
			return info, fmt.Errorf("failed to merge settings block: %w", err)
		}
	}

	// 3. Merge Manual Override (opts.Settings) on top
	if err := deepMerge(finalSettings, opts.Settings); err != nil {
		return info, fmt.Errorf("failed to merge manual settings override: %w", err)
	}
	opts.Settings = finalSettings // Update the final settings map

	// 4. Merge MCPServers into Settings if present
	if len(opts.MCPServers) > 0 {
		if opts.Settings == nil {
			opts.Settings = make(map[string]interface{})
		}

		// Get or create "mcpServers" map
		var mcpServers map[string]interface{}
		if existing, ok := opts.Settings["mcpServers"].(map[string]interface{}); ok {
			mcpServers = existing
		} else {
			mcpServers = make(map[string]interface{})
		}

		for i, mcp := range opts.MCPServers {
			// Construct the server config object
			serverConfig := make(map[string]interface{})

			// Use Content if provided (for raw JSON blocks), otherwise use fields
			if len(mcp.Content) > 0 {
				serverConfig = mcp.Content
			} else {
				// Fallback to specific fields if Content is empty (though BlockSelector usually provides Content)
				// This handles cases where config was manually defined in YAML
				if mcp.Command != "" {
					serverConfig["command"] = mcp.Command
				}
				if mcp.Url != "" {
					serverConfig["url"] = mcp.Url
				}
				if mcp.HttpUrl != "" {
					serverConfig["httpUrl"] = mcp.HttpUrl
				}
				if len(mcp.Args) > 0 {
					serverConfig["args"] = mcp.Args
				}
				if len(mcp.Env) > 0 {
					serverConfig["env"] = mcp.Env
				}
			}

			// Add to mcpServers map with the server name
			name := mcp.Name
			if name == "" {
				if mcp.Command != "" {
					name = filepath.Base(mcp.Command)
				} else {
					name = fmt.Sprintf("server-%d", i) // Fallback for list index
				}
			}
			mcpServers[name] = serverConfig
			mcpServers[name] = serverConfig
		}
		opts.Settings["mcpServers"] = mcpServers
		// DEBUG logging
		log.Printf("[Workspace] Merged MCPServers: %+v", mcpServers)
	}

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
			// DEBUG logging
			log.Printf("[Workspace] Generated settings.json at %s with content: %+v", destSettings, opts.Settings)
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

	// Handle Extensions via CLI
	if len(opts.Extensions) > 0 {
		bin := opts.Command
		if bin == "" {
			bin = "gemini"
		}
		parts := strings.Fields(bin)
		baseCmd := parts[0]
		baseArgs := parts[1:]

		for _, ext := range opts.Extensions {
			if ext.Source == "" {
				continue
			}

			// Construct arguments: extensions install/link <source>
			action := "install"
			if ext.Mode == "link" {
				action = "link"
			}
			args := append(baseArgs, "extensions", action, ext.Source)

			// Only add install-specific flags if not linking (link doesn't support them usually)
			if action == "install" {
				if ext.Ref != "" {
					args = append(args, "--ref", ext.Ref)
				}
				if ext.AutoUpdate {
					args = append(args, "--auto-update")
				}
				if ext.PreRelease {
					args = append(args, "--pre-release")
				}
			}
			// Consent applies to both install and link, and is required for non-interactive mode.
			// Since this is an automated runner, we always provide consent.
			args = append(args, "--consent")

			fmt.Printf("[Workspace] %s extension: %s (Source: %s)\n", action, ext.Name, ext.Source)
			log.Printf("[Workspace] Extension %s: HOME=%s CMD=%s %v", action, info.Home, baseCmd, args)

			cmd := exec.Command(baseCmd, args...)

			// Crucial: Set HOME to the isolated home directory.
			// Extensions always install to ~/.gemini/extensions.
			cmd.Env = os.Environ()
			cmd.Env = append(cmd.Env, fmt.Sprintf("HOME=%s", info.Home))
			// CWD doesn't matter much for extensions unless relative path source?
			// If source is local path, it must be valid relative to where we run or absolute.
			// If user provides absolute local path, it works.
			// If relative, we should run from project root? Or where tenkai is run?
			// Usually relative paths in blocks are tricky. Absolute preferred.
			cmd.Dir = info.Project

			if out, err := cmd.CombinedOutput(); err != nil {
				return info, fmt.Errorf("failed to install extension %s: %v\nOutput: %s", ext.Name, err, string(out))
			}
		}
	}

	// Handle Skills via CLI
	if len(opts.Skills) > 0 {
		// Determine the binary to use. If opts.Command is empty or just "gemini", we assume "gemini" is in PATH.
		// If it's a relative path like "./bin/gemini", we need to resolve it relative to... CWD?
		// The runner executes it relative to the workspace, but here we are in the orchestrator.
		// We should probably rely on the system "gemini" OR the one specified.
		// NOTE: If the user provides a complex command like "go run main.go", this logic might fail to install skills unless we parse it.
		// For now, we assume the command is a binary that supports 'skills install'.

		bin := opts.Command
		if bin == "" {
			bin = "gemini"
		}
		// If the command has arguments (e.g. "go run ."), we need to split it.
		// Simple split for now.
		parts := strings.Fields(bin)
		baseCmd := parts[0]
		baseArgs := parts[1:]

		for _, skill := range opts.Skills {
			if skill.Source == "" {
				continue
			}

			// Construct arguments: skills install <source>
			args := append(baseArgs, "skills", "install", skill.Source)

			if skill.Path != "" {
				args = append(args, "--path", skill.Path)
			}
			if skill.Scope != "" {
				args = append(args, "--scope", skill.Scope)
			} else {
				// Default to user scope if not specified,
				// but let's be explicit if needed. The CLI defaults to user.
			}

			fmt.Printf("[Workspace] Installing skill: %s (Source: %s)\n", skill.Name, skill.Source)
			log.Printf("[Workspace] Skill Install: HOME=%s CMD=%s %v", info.Home, baseCmd, args)

			cmd := exec.Command(baseCmd, args...)

			// Crucial: Set HOME to the isolated home directory so 'scope: user' installs there.
			// And set CWD to the project directory so 'scope: workspace' installs there.
			cmd.Env = os.Environ()
			cmd.Env = append(cmd.Env, fmt.Sprintf("HOME=%s", info.Home))
			cmd.Dir = info.Project

			if out, err := cmd.CombinedOutput(); err != nil {
				return info, fmt.Errorf("failed to install skill %s: %v\nOutput: %s", skill.Name, err, string(out))
			}
		}
	}

	// golangci-lint is pre-installed in the Docker image, so we rely on PATH.
	return info, nil
}

// deepMerge merges src into dst.
// Maps are merged recursively.
// Slices are replaced? Or appended? User requested "last merged block always win" for conflicts.
// Standard JSON merge usually replaces primitives and lists.
// However, for "tools": {"core": []}, replacing is correct.
// If we had a list of plugins, maybe we'd want append, but "last wins" usually implies overlay.
// Let's implement overlay (replace) for lists and primitives, deep merge for maps.
func deepMerge(dst, src map[string]interface{}) error {
	for key, srcVal := range src {
		// Filter out internal keys (metadata starting with _)
		if strings.HasPrefix(key, "_") {
			continue
		}

		if dstVal, ok := dst[key]; ok {
			// If both are maps, recurse
			srcMap, srcIsMap := srcVal.(map[string]interface{})
			dstMap, dstIsMap := dstVal.(map[string]interface{})
			if srcIsMap && dstIsMap {
				if err := deepMerge(dstMap, srcMap); err != nil {
					return err
				}
				continue
			}
		}
		// Otherwise, overwrite
		dst[key] = srcVal
	}
	return nil
}
