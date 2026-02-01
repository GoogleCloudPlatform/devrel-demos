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
	Scenarios     []string      `yaml:"scenarios" json:"scenarios"`
	IsLocked      bool          `yaml:"is_locked,omitempty" json:"is_locked,omitempty"`
}

// SettingsBlock represents a configuration block that can be merged.
// It supports both legacy (mixed metadata/content) and strict (content field) YAML formats.
type SettingsBlock struct {
	Name    string                 `yaml:"name,omitempty" json:"name,omitempty"`
	Content map[string]interface{} `yaml:"content" json:"content"`
}

// UnmarshalYAML implements custom unmarshaling to support legacy mixed-mode YAML.
func (sb *SettingsBlock) UnmarshalYAML(value *yaml.Node) error {
	// 1. Decode into a raw map to inspect keys
	var raw map[string]interface{}
	if err := value.Decode(&raw); err != nil {
		return err
	}

	// 2. Check for explicit "content" map (New Strict Format)
	if c, ok := raw["content"]; ok {
		// If "content" exists and is a map, we assume strict mode.
		// We re-decode into the struct to leverage standard YAML type mapping for the map.
		// (Or just use raw, but raw might have mixed map types if not careful, though Decode handles it).
		// Let's just manually extract from raw to avoid re-parsing overhead.

		if name, ok := raw["name"].(string); ok {
			sb.Name = name
		}

		if contentMap, ok := c.(map[string]interface{}); ok {
			sb.Content = contentMap
		} else if _, ok := c.(map[interface{}]interface{}); ok {
			// Convert if it came out as interface map (unlikely with Decode(&raw) but safe to handle)
			// Actually Decode(&raw) where raw is map[string]interface{} forces string keys for top level.
			// But values might be mixed. We assign it, deepMerge handles values.
			// But we need map[string]interface{}.
			// Let's rely on re-decoding to struct for safety if content is complex.
			type strict struct {
				Name    string                 `yaml:"name"`
				Content map[string]interface{} `yaml:"content"`
			}
			var s strict
			if err := value.Decode(&s); err != nil {
				return err
			}
			sb.Name = s.Name
			sb.Content = s.Content
			return nil
		} else {
			// content is not a map? (e.g. null).
			sb.Content = make(map[string]interface{})
		}
		return nil
	}

	// 3. Legacy Mixed Format (Metadata sibling to Content)
	sb.Content = make(map[string]interface{})
	for k, v := range raw {
		if k == "name" {
			if n, ok := v.(string); ok {
				sb.Name = n
				continue
			}
		}
		// Treat everything else as content
		sb.Content[k] = v
	}
	return nil
}

// Alternative represents a specific agent configuration.
type Alternative struct {
	Name             string                 `yaml:"name" json:"name"`
	Description      string                 `yaml:"description,omitempty" json:"description,omitempty"`
	Command          string                 `yaml:"command" json:"command"`
	Args             []string               `yaml:"args" json:"args"`
	Env              map[string]string      `yaml:"env,omitempty" json:"env,omitempty"`
	SettingsPath     string                 `yaml:"settings_path,omitempty" json:"settings_path,omitempty"`     // Path to settings.json
	Settings         map[string]interface{} `yaml:"settings,omitempty" json:"settings,omitempty"`               // Inline settings object (Final Override)
	SettingsBlocks   []SettingsBlock        `yaml:"settings_blocks,omitempty" json:"settings_blocks,omitempty"` // List of settings blocks to merge
	SystemPromptFile string                 `yaml:"system_prompt_file,omitempty" json:"system_prompt_file,omitempty"`
	SystemPrompt     string                 `yaml:"system_prompt,omitempty" json:"system_prompt,omitempty"`         // Inline system prompt content
	ContextFilePath  string                 `yaml:"context_file_path,omitempty" json:"context_file_path,omitempty"` // Path to file to copy as GEMINI.md
	Context          string                 `yaml:"context,omitempty" json:"context,omitempty"`                     // Inline GEMINI.md content
	PolicyFiles      []string               `yaml:"policy_files,omitempty" json:"policy_files,omitempty"`           // Paths to files to copy to .gemini/policies/
	Extensions       []ExtensionConfig      `yaml:"extensions,omitempty" json:"extensions,omitempty"`
	Skills           []SkillConfig          `yaml:"skills,omitempty" json:"skills,omitempty"`
	MCPServers       []MCPConfig            `yaml:"mcp_servers,omitempty" json:"mcp_servers,omitempty"`
}

// MCPConfig defines a Model Context Protocol server configuration block.
// This is typically a raw map that gets merged into "settings.mcpServers".
type MCPConfig struct {
	Name    string                 `yaml:"name" json:"name"`
	Command string                 `yaml:"command,omitempty" json:"command,omitempty"`
	URL     string                 `yaml:"url,omitempty" json:"url,omitempty"`
	HTTPURL string                 `yaml:"httpUrl,omitempty" json:"httpUrl,omitempty"`
	Args    []string               `yaml:"args,omitempty" json:"args,omitempty"`
	Env     map[string]string      `yaml:"env,omitempty" json:"env,omitempty"`
	Content map[string]interface{} `yaml:"content,omitempty" json:"content,omitempty"` // For advanced config (trust, includeTools, etc)
}

// ExtensionConfig defines an extension to be installed in the workspace.
type ExtensionConfig struct {
	Name       string `yaml:"name" json:"name"`
	Source     string `yaml:"source" json:"source"`                 // URL or Local Path
	Ref        string `yaml:"ref,omitempty" json:"ref,omitempty"`   // Git Ref
	Mode       string `yaml:"mode,omitempty" json:"mode,omitempty"` // "install" (default) or "link"
	AutoUpdate bool   `yaml:"auto_update,omitempty" json:"auto_update,omitempty"`
	PreRelease bool   `yaml:"pre_release,omitempty" json:"pre_release,omitempty"`
	Consent    bool   `yaml:"consent,omitempty" json:"consent,omitempty"`
}

// SkillConfig defines an agent skill to be installed.
type SkillConfig struct {
	Name   string `yaml:"name" json:"name"`
	Source string `yaml:"source" json:"source"`                   // URL, Local Path, or Zip file
	Path   string `yaml:"path,omitempty" json:"path,omitempty"`   // Optional subpath (for --path)
	Scope  string `yaml:"scope,omitempty" json:"scope,omitempty"` // "user" or "workspace"
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
	Type              string   `yaml:"type" json:"type"`
	Target            string   `yaml:"target,omitempty" json:"target,omitempty"`
	MinCoverage       float64  `yaml:"min_coverage,omitempty" json:"min_coverage,omitempty"`
	MaxIssues         int      `yaml:"max_issues,omitempty" json:"max_issues,omitempty"`
	Exclude           []string `yaml:"exclude,omitempty" json:"exclude,omitempty"`
	Prompt            string   `yaml:"prompt,omitempty" json:"prompt,omitempty"`
	Context           []string `yaml:"context,omitempty" json:"context,omitempty"`
	Command           string   `yaml:"command,omitempty" json:"command,omitempty"`
	Args              []string `yaml:"args,omitempty" json:"args,omitempty"`
	Stdin             string   `yaml:"stdin,omitempty" json:"stdin,omitempty"`
	StdinDelay        string   `yaml:"stdin_delay,omitempty" json:"stdin_delay,omitempty"` // e.g. "500ms", "1s"
	ExpectExitCode    *int     `yaml:"expect_exit_code,omitempty" json:"expect_exit_code,omitempty"`
	ExpectOutput      string   `yaml:"expect_output,omitempty" json:"expect_output,omitempty"`
	ExpectOutputRegex string   `yaml:"expect_output_regex,omitempty" json:"expect_output_regex,omitempty"`
}

// ScenarioConfig represents the content of a scenario.yaml file.
type ScenarioConfig struct {
	Name        string           `yaml:"name" json:"name"`
	Description string           `yaml:"description,omitempty" json:"description,omitempty"`
	Task        string           `yaml:"task,omitempty" json:"task,omitempty"`
	GithubIssue string           `yaml:"github_issue,omitempty" json:"github_issue,omitempty"`
	Assets      []Asset          `yaml:"assets" json:"assets"`
	Validation  []ValidationRule `yaml:"validation" json:"validation"`
	IsLocked    bool             `yaml:"is_locked,omitempty" json:"is_locked,omitempty"`
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

// Parse unmarshals configuration from byte slice.
func Parse(data []byte) (*Configuration, error) {
	var cfg Configuration
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config data: %w", err)
	}

	// We can't easily resolve relative paths here because we don't know the config file path.
	// But in the Worker context, dependencies (assets) are usually handled differently or we expect absolute paths/standalone.
	// For now, we return as is. The Worker might need to handle asset copying if they are relative.
	// However, `Scenario.yaml` assets are likely copied into the experiment workspace already?
	// No, `prepareWorkspaceForRun` copies them.
	// If paths are relative in config, `prepareWorkspaceForRun` resolves them against `ConfigDir`.
	// Since we are reconstructing from DB content, we lose `ConfigDir`.
	// This might be an issue if assets are relative.
	// But `StartExperiment` saves `EffectiveConfig`?
	// `RunResults` doesn't store the full config path context.
	// `experiments` table stores `config_path`. We can maybe verify if we can access the original files?
	// On Cloud Run, we definitely can't access original files from the path.
	// We might need to bundle assets or assume they are in the image.
	// For now, let's assume assets are available or paths are handled.

	return &cfg, nil
}
