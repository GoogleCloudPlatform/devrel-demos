package config

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

// Configuration holds the experiment definition.
type Configuration struct {
	Name          string        `yaml:"name" json:"name"`
	Description   string        `yaml:"description,omitempty" json:"description,omitempty"`
	Repetitions   int           `yaml:"repetitions,omitempty" json:"repetitions,omitempty"`
	MaxConcurrent int           `yaml:"max_concurrent,omitempty" json:"max_concurrent,omitempty"`
	Timeout       string        `yaml:"timeout,omitempty" json:"timeout,omitempty"`                       // e.g. "5m", "10m"
	Control       string        `yaml:"experiment_control,omitempty" json:"experiment_control,omitempty"` // Name of the control alternative
	Alternatives  []Alternative `yaml:"alternatives" json:"alternatives"`
	// Alternatives is already defined above
	Scenarios []string `yaml:"scenarios" json:"scenarios"`
}

// Alternative represents a specific agent configuration.
type Alternative struct {
	Name             string                 `yaml:"name" json:"name"`
	Description      string                 `yaml:"description,omitempty" json:"description,omitempty"`
	Command          string                 `yaml:"command" json:"command"`
	Args             []string               `yaml:"args" json:"args"`
	Env              map[string]string      `yaml:"env,omitempty" json:"env,omitempty"`
	SettingsPath     string                 `yaml:"settings_path,omitempty" json:"settings_path,omitempty"` // Path to settings.json
	Settings         map[string]interface{} `yaml:"settings,omitempty" json:"settings,omitempty"`           // Inline settings object
	SystemPromptFile string                 `yaml:"system_prompt_file,omitempty" json:"system_prompt_file,omitempty"`
	SystemPrompt     string                 `yaml:"system_prompt,omitempty" json:"system_prompt,omitempty"`         // Inline system prompt content
	ContextFilePath  string                 `yaml:"context_file_path,omitempty" json:"context_file_path,omitempty"` // Path to file to copy as GEMINI.md
	Context          string                 `yaml:"context,omitempty" json:"context,omitempty"`                     // Inline GEMINI.md content
	PolicyFiles      []string               `yaml:"policy_files,omitempty" json:"policy_files,omitempty"`           // Paths to files to copy to .gemini/policies/
}

// Asset represents a file or directory to be set up in the workspace.
type Asset struct {
	Type    string `yaml:"type" json:"type"`
	Source  string `yaml:"source,omitempty" json:"source,omitempty"`
	Target  string `yaml:"target" json:"target"`
	Ref     string `yaml:"ref,omitempty" json:"ref,omitempty"`
	Content string `yaml:"content,omitempty" json:"content,omitempty"`
}

// ValidationRule defines a success criterion for the scenario.
type ValidationRule struct {
	Type           string            `yaml:"type" json:"type"`
	Target         string            `yaml:"target,omitempty" json:"target,omitempty"`
	MinCoverage    float64           `yaml:"min_coverage,omitempty" json:"min_coverage,omitempty"`
	MaxIssues      int               `yaml:"max_issues,omitempty" json:"max_issues,omitempty"`
	Exclude        []string          `yaml:"exclude,omitempty" json:"exclude,omitempty"`
	Prompt         string            `yaml:"prompt,omitempty" json:"prompt,omitempty"`
	Context        []string          `yaml:"context,omitempty" json:"context,omitempty"`
	Command        string            `yaml:"command,omitempty" json:"command,omitempty"`
	Args           []string          `yaml:"args,omitempty" json:"args,omitempty"`
	Env            map[string]string `yaml:"env,omitempty" json:"env,omitempty"`                             // Environment variables for the validation command
	ExpectExitCode int               `yaml:"expect_exit_code,omitempty" json:"expected_exit_code,omitempty"` // Frontend expects expected_exit_code
	ExpectOutput   string            `yaml:"expect_output,omitempty" json:"expect_output,omitempty"`
}

// ScenarioConfig represents the content of a scenario.yaml file.
type ScenarioConfig struct {
	Name        string           `yaml:"name" json:"name"`
	Description string           `yaml:"description,omitempty" json:"description,omitempty"`
	Task        string           `yaml:"task,omitempty" json:"task,omitempty"`
	GithubIssue string           `yaml:"github_issue,omitempty" json:"github_issue,omitempty"`
	Assets      []Asset          `yaml:"assets" json:"assets"`
	Validation  []ValidationRule `yaml:"validation" json:"validation"`
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

	fmt.Printf("[Config] Loaded %d scenarios\n", len(cfg.Scenarios))

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
