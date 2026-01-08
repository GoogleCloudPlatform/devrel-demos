package workspace

import (
	"archive/zip"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"gopkg.in/yaml.v3"
)

// Scenario represents a discoverable scenario.
type Scenario struct {
	ID          string                  `json:"id"`
	Name        string                  `json:"name"`
	Description string                  `json:"description"`
	Path        string                  `json:"path"`
	Task        string                  `json:"task,omitempty"`
	Validation  []config.ValidationRule `json:"validation,omitempty"`
}

// Template represents a reusable experiment configuration.
type Template struct {
	ID            string   `json:"id"`
	Name          string   `json:"name"`
	Description   string   `json:"description"`
	Path          string   `json:"path"`
	ConfigContent string   `json:"config_content,omitempty"` // For detail view
	AltCount      int      `json:"alt_count"`
	ScenCount     int      `json:"scen_count"`
	Alternatives  []string `json:"alternatives"`
	Reps          int      `json:"reps"`
}

// WorkspaceInfo contains the paths for a prepared workspace.
type WorkspaceInfo struct {
	Root    string
	Project string
	Home    string
	Logs    string
	Config  *config.ScenarioConfig // Passed in-memory to avoid reloading from disk
}

// Manager handles the creation and setup of isolated workspaces for experiments.
type Manager struct {
	BasePath      string
	TemplatesDirs []string
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

// New creates a new Workspace Manager.
func New(basePath string, templatesDirs ...string) *Manager {
	return &Manager{
		BasePath:      basePath,
		TemplatesDirs: templatesDirs,
	}
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
		for _, asset := range scenCfg.Assets {

			targetPath := filepath.Join(info.Project, asset.Target)
			if asset.Target == "." {
				targetPath = info.Project
			}

			switch asset.Type {
			case "directory":
				src := filepath.Join(tmplPath, asset.Source)
				if err := copyDir(src, targetPath); err != nil {
					return info, fmt.Errorf("failed to copy directory asset %s: %w", src, err)
				}
			case "file":
				if asset.Content != "" {
					if err := os.WriteFile(targetPath, []byte(asset.Content), 0644); err != nil {
						return info, fmt.Errorf("failed to write inline file asset %s: %w", targetPath, err)
					}
				} else {
					src := filepath.Join(tmplPath, asset.Source)
					if err := copyFile(src, targetPath); err != nil {
						return info, fmt.Errorf("failed to copy file asset %s: %w", src, err)
					}
				}
			case "git":
				if err := setupGit(asset.Source, asset.Ref, targetPath); err != nil {
					return info, fmt.Errorf("failed to setup git asset %s: %w", asset.Source, err)
				}
			case "zip":
				if err := setupZip(asset.Source, targetPath); err != nil {
					return info, fmt.Errorf("failed to setup zip asset %s: %w", asset.Source, err)
				}
			}
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
		// Legacy mode: Copy entire directory to project
		if err := copyDir(tmplPath, info.Project); err != nil {
			return info, fmt.Errorf("failed to copy template from %s to %s: %w", tmplPath, info.Project, err)
		}
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

// ListScenarios returns a list of available scenarios found in the templates directories.
func (m *Manager) ListScenarios() []Scenario {
	var scenarios []Scenario
	seen := make(map[string]bool)

	for _, dir := range m.TemplatesDirs {
		entries, err := os.ReadDir(dir)
		if err != nil {
			log.Printf("Warning: failed to read templates dir %s: %v", dir, err)
			continue
		}

		for _, entry := range entries {
			if !entry.IsDir() {
				continue
			}

			name := entry.Name()
			if seen[name] {
				continue
			}

			// Check for scenario.yaml to get description
			scen := Scenario{
				ID:   name,
				Name: name, // Default
				Path: filepath.Join(dir, name),
			}

			configPath := filepath.Join(dir, name, "scenario.yaml")
			if cfg, err := config.LoadScenarioConfig(configPath); err == nil {
				if cfg.Name != "" {
					scen.Name = cfg.Name
				}
				scen.Description = cfg.Description
				scen.Task = cfg.Task
				scen.Validation = cfg.Validation
			}

			scenarios = append(scenarios, scen)
			seen[name] = true
		}
	}
	return scenarios
}

// GetScenario returns the details of a specific scenario by ID.
func (m *Manager) GetScenario(id string) (*Scenario, error) {
	for _, dir := range m.TemplatesDirs {
		path := filepath.Join(dir, id)
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			scen := &Scenario{
				ID:   id,
				Name: id,
				Path: path,
			}

			configPath := filepath.Join(path, "scenario.yaml")
			if cfg, err := config.LoadScenarioConfig(configPath); err == nil {
				if cfg.Name != "" {
					scen.Name = cfg.Name
				}
				scen.Description = cfg.Description
				scen.Task = cfg.Task
				scen.Validation = cfg.Validation
			}
			return scen, nil
		}
	}
	return nil, fmt.Errorf("scenario %q not found", id)
}

// ListTemplates returns a list of available templates found in the experiments/templates directory.
func (m *Manager) ListTemplates() []Template {
	var templates []Template

	// Assume standard location relative to BasePath
	templatesBase := filepath.Join(m.BasePath, "experiments", "templates")
	entries, err := os.ReadDir(templatesBase)
	if err != nil {
		// It's okay if it doesn't exist yet
		return templates
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		id := entry.Name()
		configPath := filepath.Join(templatesBase, id, "config.yaml")

		// Parse config to get details
		cfg, err := config.Load(configPath)
		if err != nil {
			log.Printf("Warning: failed to load template config %s: %v", configPath, err)
			continue
		}

		contentBytes, _ := os.ReadFile(configPath)

		tmpl := Template{
			ID:            id,
			Name:          cfg.Name,
			Description:   cfg.Description,
			Path:          configPath,
			ConfigContent: string(contentBytes),
			AltCount:      len(cfg.Alternatives),
			ScenCount:     len(cfg.Scenarios),
			Reps:          cfg.Repetitions,
		}
		for _, a := range cfg.Alternatives {
			tmpl.Alternatives = append(tmpl.Alternatives, a.Name)
		}

		templates = append(templates, tmpl)
	}
	return templates
}

// GetTemplate returns the details of a specific template by ID.
func (m *Manager) GetTemplate(id string) (*Template, error) {
	templatesBase := filepath.Join(m.BasePath, "experiments", "templates")
	path := filepath.Join(templatesBase, id)
	configPath := filepath.Join(path, "config.yaml")

	if info, err := os.Stat(path); err == nil && info.IsDir() {
		// Found directory, now load config
		cfg, err := config.Load(configPath)
		if err != nil {
			return nil, fmt.Errorf("failed to load template config: %w", err)
		}

		contentBytes, _ := os.ReadFile(configPath)

		tmpl := &Template{
			ID:            id,
			Name:          cfg.Name,
			Description:   cfg.Description,
			Path:          configPath,
			ConfigContent: string(contentBytes),
			AltCount:      len(cfg.Alternatives),
			ScenCount:     len(cfg.Scenarios),
			Reps:          cfg.Repetitions,
		}
		for _, a := range cfg.Alternatives {
			tmpl.Alternatives = append(tmpl.Alternatives, a.Name)
		}
		return tmpl, nil
	}

	return nil, fmt.Errorf("template %q not found", id)
}

// Helper to normalize configuration (e.g. inject default args)
func (m *Manager) normalizeConfig(content string) (string, error) {
	var cfg config.Configuration
	if err := yaml.Unmarshal([]byte(content), &cfg); err != nil {
		// If it's a partial config (template) it might not match Configuration struct exactly?
		// Template config should match.
		return content, nil
	}

	modified := false
	for i, alt := range cfg.Alternatives {
		if filepath.Base(alt.Command) == "gemini" {
			hasY := false
			hasO := false
			for idx, arg := range alt.Args {
				if arg == "-y" {
					hasY = true
				}
				if arg == "-o" && idx+1 < len(alt.Args) && alt.Args[idx+1] == "stream-json" {
					hasO = true
				}
			}
			if !hasY {
				// Prepend -y
				cfg.Alternatives[i].Args = append([]string{"-y"}, cfg.Alternatives[i].Args...)
				modified = true
			}
			if !hasO {
				// Append -o stream-json
				cfg.Alternatives[i].Args = append(cfg.Alternatives[i].Args, "-o", "stream-json")
				modified = true
			}
		}
	}

	if modified {
		data, err := yaml.Marshal(cfg)
		if err != nil {
			return "", err
		}
		return string(data), nil
	}
	return content, nil
}

// CreateTemplate creates a new template directory and config file.
func (m *Manager) CreateTemplate(name, description, configContent string, files map[string]string) (string, error) {
	templatesBase := filepath.Join(m.BasePath, "experiments", "templates")
	if err := os.MkdirAll(templatesBase, 0755); err != nil {
		return "", err
	}

	id := fmt.Sprintf("%d", GetTimestampID())

	tmplDir := filepath.Join(templatesBase, id)
	if err := os.MkdirAll(tmplDir, 0755); err != nil {
		return "", err
	}

	// Normalize config content
	normConfig, err := m.normalizeConfig(configContent)
	if err != nil {
		log.Printf("Warning: failed to normalize config: %v", err)
		normConfig = configContent
	}

	// Write config.yaml
	if err := os.WriteFile(filepath.Join(tmplDir, "config.yaml"), []byte(normConfig), 0644); err != nil {
		return "", err
	}

	// Write extra files (SYSTEM.md, GEMINI.md, settings.json)
	for fname, content := range files {
		// Basic sanitization
		fname = filepath.Base(fname)
		if err := os.WriteFile(filepath.Join(tmplDir, fname), []byte(content), 0644); err != nil {
			return "", fmt.Errorf("failed to write file %s: %w", fname, err)
		}
	}

	return id, nil
}

// UpdateTemplate updates an existing template configuration.
func (m *Manager) UpdateTemplate(id, configContent string, files map[string]string) error {
	templatesBase := filepath.Join(m.BasePath, "experiments", "templates")
	tmplDir := filepath.Join(templatesBase, id)
	configPath := filepath.Join(tmplDir, "config.yaml")

	if _, err := os.Stat(tmplDir); os.IsNotExist(err) {
		return fmt.Errorf("template %q not found", id)
	}

	// Normalize config content
	normConfig, err := m.normalizeConfig(configContent)
	if err != nil {
		log.Printf("Warning: failed to normalize config: %v", err)
		normConfig = configContent
	}

	// Write config.yaml
	if err := os.WriteFile(configPath, []byte(normConfig), 0644); err != nil {
		return err
	}

	// Write extra files
	for fname, content := range files {
		fname = filepath.Base(fname)
		if err := os.WriteFile(filepath.Join(tmplDir, fname), []byte(content), 0644); err != nil {
			return fmt.Errorf("failed to write file %s: %w", fname, err)
		}
	}
	return nil
}

// DeleteTemplate deletes a template directory.
func (m *Manager) DeleteTemplate(id string) error {
	templatesBase := filepath.Join(m.BasePath, "experiments", "templates")
	path := filepath.Join(templatesBase, id)
	if _, err := os.Stat(path); err == nil {
		return os.RemoveAll(path)
	}
	return fmt.Errorf("template %q not found", id)
}

// DeleteAllTemplates deletes all templates.
func (m *Manager) DeleteAllTemplates() error {
	templatesBase := filepath.Join(m.BasePath, "experiments", "templates")
	entries, err := os.ReadDir(templatesBase)
	if err != nil {
		return nil // Ignore if dir doesn't exist
	}
	for _, entry := range entries {
		if entry.IsDir() {
			os.RemoveAll(filepath.Join(templatesBase, entry.Name()))
		}
	}
	return nil
}

// Helper for ID generation

func GetTimestampID() int64 {
	return time.Now().UnixNano()
}

// CreateScenario creates a new scenario directory and assets.
func (m *Manager) CreateScenario(name, description, task string, assets []config.Asset, validation []config.ValidationRule) (string, error) {
	// Use the first templates dir for creation (usually scenarios/)
	if len(m.TemplatesDirs) == 0 {
		return "", fmt.Errorf("no templates directory configured")
	}
	baseDir := m.TemplatesDirs[0]

	id := fmt.Sprintf("%d", time.Now().UnixNano())

	scenDir := filepath.Join(baseDir, id)
	if err := os.MkdirAll(scenDir, 0755); err != nil {
		return "", err
	}

	// Create scenario.yaml
	cfg := config.ScenarioConfig{
		Name:        name,
		Description: description,
		Task:        task,
		Assets:      assets,
		Validation:  validation,
	}

	data, err := yaml.Marshal(cfg)
	if err != nil {
		return "", err
	}

	if err := os.WriteFile(filepath.Join(scenDir, "scenario.yaml"), data, 0644); err != nil {
		return "", err
	}

	// Also write PROMPT.md for legacy compatibility/easier reading
	if task != "" {
		if err := os.WriteFile(filepath.Join(scenDir, "PROMPT.md"), []byte(task), 0644); err != nil {
			return "", err
		}
	}
	return id, nil
}

// UpdateScenario updates an existing scenario configuration.
func (m *Manager) UpdateScenario(id, name, description, task string, validation []config.ValidationRule) error {
	for _, dir := range m.TemplatesDirs {
		path := filepath.Join(dir, id)
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			// Update scenario.yaml
			configPath := filepath.Join(path, "scenario.yaml")
			var cfg config.ScenarioConfig
			if existing, err := config.LoadScenarioConfig(configPath); err == nil {
				cfg = *existing // Preserve assets and other fields not being updated
			}

			// Update fields
			cfg.Name = name
			cfg.Description = description
			if task != "" {
				cfg.Task = task
			}
			cfg.Validation = validation

			data, err := yaml.Marshal(cfg)
			if err != nil {
				return err
			}

			if err := os.WriteFile(configPath, data, 0644); err != nil {
				return err
			}

			// Update PROMPT.md if task changed
			if task != "" {
				if err := os.WriteFile(filepath.Join(path, "PROMPT.md"), []byte(task), 0644); err != nil {
					return err
				}
			}
			return nil
		}
	}
	return fmt.Errorf("scenario %q not found", id)
}

// DeleteScenario deletes a scenario directory.
func (m *Manager) DeleteScenario(id string) error {
	for _, dir := range m.TemplatesDirs {
		path := filepath.Join(dir, id)
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			return os.RemoveAll(path)
		}
	}
	return fmt.Errorf("scenario %q not found", id)
}

func copyDir(src, dst string) error {

	entries, err := os.ReadDir(src)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		dstPath := filepath.Join(dst, entry.Name())

		if entry.IsDir() {
			if err := os.MkdirAll(dstPath, 0755); err != nil {
				return err
			}
			if err := copyDir(srcPath, dstPath); err != nil {
				return err
			}
		} else {
			if err := copyFile(srcPath, dstPath); err != nil {
				return err
			}
		}
	}
	return nil
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}

func setupGit(repoURL, ref, targetDir string) error {
	// 1. Clone
	cmd := exec.Command("git", "clone", repoURL, targetDir)
	if out, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("git clone failed: %s (%w)", string(out), err)
	}

	// 2. Checkout ref if provided
	if ref != "" {
		cmd = exec.Command("git", "checkout", ref)
		cmd.Dir = targetDir
		if out, err := cmd.CombinedOutput(); err != nil {
			return fmt.Errorf("git checkout failed: %s (%w)", string(out), err)
		}
	}
	return nil
}

func setupZip(url, targetDir string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// Create a temp file to store the zip
	tmpFile, err := os.CreateTemp("", "tenkai-asset-*.zip")
	if err != nil {
		return err
	}
	defer os.Remove(tmpFile.Name())

	_, err = io.Copy(tmpFile, resp.Body)
	if err != nil {
		return err
	}
	tmpFile.Close()

	// Unzip
	r, err := zip.OpenReader(tmpFile.Name())
	if err != nil {
		return err
	}
	defer r.Close()

	for _, f := range r.File {
		fpath := filepath.Join(targetDir, f.Name)

		if f.FileInfo().IsDir() {
			os.MkdirAll(fpath, os.ModePerm)
			continue
		}

		if err := os.MkdirAll(filepath.Dir(fpath), os.ModePerm); err != nil {
			return err
		}

		outFile, err := os.OpenFile(fpath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
		if err != nil {
			return err
		}

		rc, err := f.Open()
		if err != nil {
			outFile.Close()
			return err
		}

		_, err = io.Copy(outFile, rc)

		outFile.Close()
		rc.Close()
	}
	return nil
}

type githubIssue struct {
	Title string `json:"title"`
	Body  string `json:"body"`
}

func fetchGithubIssue(issueURL string) (*githubIssue, error) {
	// Parse URL: https://github.com/owner/repo/issues/number
	parts := strings.Split(issueURL, "/")
	if len(parts) < 7 {
		return nil, fmt.Errorf("invalid github issue url format")
	}
	owner := parts[3]
	repo := parts[4]
	number := parts[6]

	apiURL := fmt.Sprintf("https://api.github.com/repos/%s/%s/issues/%s", owner, repo, number)
	resp, err := http.Get(apiURL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("github api returned status %d", resp.StatusCode)
	}

	var issue githubIssue
	if err := json.NewDecoder(resp.Body).Decode(&issue); err != nil {
		return nil, err
	}
	return &issue, nil
}
