package config

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

// Configuration holds the experiment definition.
type Configuration struct {
	Name          string        `yaml:"name"`
	Description   string        `yaml:"description,omitempty"`
	Repetitions   int           `yaml:"repetitions,omitempty"`
	MaxConcurrent int           `yaml:"max_concurrent,omitempty"`
	Timeout       string        `yaml:"timeout,omitempty"` // e.g. "5m", "10m"
	Control       string        `yaml:"control,omitempty"` // Name of the control alternative
	Alternatives  []Alternative `yaml:"alternatives"`
	Scenarios     []Scenario    `yaml:"scenarios"`
}

// Alternative represents a specific agent configuration.
type Alternative struct {
	Name             string            `yaml:"name"`
	Description      string            `yaml:"description,omitempty"`
	Command          string            `yaml:"command"`
	Args             []string          `yaml:"args"`
	Env              map[string]string `yaml:"env,omitempty"`
	SettingsPath     string            `yaml:"settings_path,omitempty"` // Path to mcp settings.json
	SystemPromptFile string            `yaml:"system_prompt_file,omitempty"`
	ContextFilePath  string            `yaml:"context_file_path,omitempty"` // Path to file to copy as GEMINI.md
	PolicyFiles      []string          `yaml:"policy_files,omitempty"`      // Paths to files to copy to .gemini/policies/
}

// Scenario represents a coding task template in the main config.
type Scenario struct {
	Name        string `yaml:"name"`
	Description string `yaml:"description,omitempty"`
}

// Asset represents a file or directory to be set up in the workspace.
type Asset struct {
	Type    string `yaml:"type"`              // "file", "directory", "git", "zip"
	Source  string `yaml:"source,omitempty"`  // Source path or URL
	Target  string `yaml:"target"`            // Destination path relative to workspace
	Ref     string `yaml:"ref,omitempty"`     // Git ref (tag, branch, commit)
	Content string `yaml:"content,omitempty"` // Inline content for files
}

// ValidationRule defines a success criterion for the scenario.
type ValidationRule struct {
	Type           string   `yaml:"type"` // "test", "lint", "model", "command"
	Target         string   `yaml:"target,omitempty"`
	MinCoverage    float64  `yaml:"min_coverage,omitempty"`
	MaxIssues      int      `yaml:"max_issues,omitempty"`
	Exclude        []string `yaml:"exclude,omitempty"`
	PromptFile     string   `yaml:"prompt_file,omitempty"`
	Context        []string `yaml:"context,omitempty"`
	Command        string   `yaml:"command,omitempty"`
	Args           []string `yaml:"args,omitempty"`
	ExpectExitCode int      `yaml:"expect_exit_code,omitempty"`
	ExpectOutput   string   `yaml:"expect_output,omitempty"`
}

// ScenarioConfig represents the content of a scenario.yaml file.
type ScenarioConfig struct {
	Name        string           `yaml:"name"`
	Description string           `yaml:"description,omitempty"`
	Task        string           `yaml:"task,omitempty"`
	GithubIssue string           `yaml:"github_issue,omitempty"`
	Assets      []Asset          `yaml:"assets"`
	Validation  []ValidationRule `yaml:"validation"`
}

// Load reads the configuration from the specified file path.
func Load(path string) (*Configuration, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var cfg Configuration
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	// Resolve relative paths against the config file directory
	configDir := filepath.Dir(path)
	for i := range cfg.Alternatives {
		alt := &cfg.Alternatives[i]
		if alt.SettingsPath != "" && !filepath.IsAbs(alt.SettingsPath) {
			alt.SettingsPath = filepath.Join(configDir, alt.SettingsPath)
		}
		if alt.SystemPromptFile != "" && !filepath.IsAbs(alt.SystemPromptFile) {
			alt.SystemPromptFile = filepath.Join(configDir, alt.SystemPromptFile)
		}
		if alt.ContextFilePath != "" && !filepath.IsAbs(alt.ContextFilePath) {
			alt.ContextFilePath = filepath.Join(configDir, alt.ContextFilePath)
		}
		for j := range alt.PolicyFiles {
			if !filepath.IsAbs(alt.PolicyFiles[j]) {
				alt.PolicyFiles[j] = filepath.Join(configDir, alt.PolicyFiles[j])
			}
		}
	}

	// Set defaults if not provided
	if cfg.Repetitions == 0 {
		cfg.Repetitions = 1
	}
	if cfg.MaxConcurrent == 0 {
		cfg.MaxConcurrent = 1
	}

	return &cfg, nil
}

// LoadScenarioConfig reads the scenario configuration from the specified file path.
func LoadScenarioConfig(path string) (*ScenarioConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read scenario config file: %w", err)
	}

	var cfg ScenarioConfig
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse scenario config file: %w", err)
	}

	return &cfg, nil
}
