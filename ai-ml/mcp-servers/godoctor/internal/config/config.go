// Package config handles configuration loading for the application.
package config

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"strings"

	"github.com/danicat/godoctor/internal/toolnames"
)

// Profile defines the operating mode of the server.
type Profile string

const (
	ProfileStandard Profile = "standard"
	ProfileFull     Profile = "full"
	ProfileOracle   Profile = "oracle"
	ProfileDynamic  Profile = "dynamic"
)

// Config holds the application configuration.
type Config struct {
	ListenAddr    string
	Version       bool
	Agents        bool
	ListTools     bool // List available tools for the selected profile and exit
	DefaultModel  string
	Profile       Profile
	AllowedTools  map[string]bool // If non-empty, ONLY these tools are allowed (after profile expansion)
	DisabledTools map[string]bool // These tools are explicitly disabled
}

// Load parses command-line arguments and returns a Config struct.
func Load(args []string) (*Config, error) {
	fs := flag.NewFlagSet("godoctor", flag.ContinueOnError)
	versionFlag := fs.Bool("version", false, "print the version and exit")
	agentsFlag := fs.Bool("agents", false, "print LLM agent instructions and exit")
	listToolsFlag := fs.Bool("list-tools", false, "list available tools for the selected profile and exit")
	toolConfigFlag := fs.String("tool-config", "", "path to tool definition overrides JSON file")
	listenAddr := fs.String("listen", "", "listen address for HTTP transport (e.g., :8080)")
	defaultModel := fs.String("model", "gemini-2.5-pro", "default Gemini model to use")
	profileFlag := fs.String("profile", "standard", "server profile: standard, full, oracle")
	allowFlag := fs.String("allow", "", "comma-separated list of tools to explicitly allow (overrides profile defaults)")
	disableFlag := fs.String("disable", "", "comma-separated list of tools to disable")

	// Legacy flag for backward compatibility, mapped to "full" profile conceptually or ignored if profile is set
	experimentalFlag := fs.Bool("experimental", false, "[deprecated] enable experimental features (use --profile=full)")

	if err := fs.Parse(args); err != nil {
		return nil, err
	}

	// Load Tool Overrides if specified
	if *toolConfigFlag != "" {
		if err := loadToolConfig(*toolConfigFlag); err != nil {
			return nil, fmt.Errorf("failed to load tool config: %w", err)
		}
	}

	profile := Profile(*profileFlag)
	if *experimentalFlag && profile == ProfileStandard {
		profile = ProfileFull
	}

	switch profile {
	case ProfileStandard, ProfileFull, ProfileOracle, ProfileDynamic:
		// valid
	default:
		return nil, fmt.Errorf("invalid profile: %s", profile)
	}

	parseList := func(s string) map[string]bool {
		m := make(map[string]bool)
		if s == "" {
			return m
		}
		for _, name := range strings.Split(s, ",") {
			trimmed := strings.TrimSpace(name)
			if trimmed != "" {
				m[trimmed] = true
			}
		}
		return m
	}

	cfg := &Config{
		ListenAddr:    *listenAddr,
		Version:       *versionFlag,
		Agents:        *agentsFlag,
		ListTools:     *listToolsFlag,
		DefaultModel:  *defaultModel,
		Profile:       profile,
		AllowedTools:  parseList(*allowFlag),
		DisabledTools: parseList(*disableFlag),
	}

	return cfg, nil
}

func loadToolConfig(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}

	var overrides map[string]toolnames.ToolConfigEntry
	if err := json.Unmarshal(data, &overrides); err != nil {
		return err
	}

	toolnames.ApplyOverrides(overrides)
	return nil
}


// IsToolEnabled checks if a tool should be enabled based on the current profile and overrides.
// 'experimental' indicates if the tool is considered experimental (legacy concept, now mostly handled by profiles).
func (c *Config) IsToolEnabled(name string, experimental bool) bool {
	// 1. Explicitly Disabled?
	// Users likely use External Name in flags, but we receive Internal Name here.
	externalName := toolnames.Registry[name].ExternalName
	if externalName == "" {
		externalName = name // Fallback
	}

	if c.DisabledTools[externalName] || c.DisabledTools[name] {
		return false
	}

	// 2. Explicitly Allowed?
	if c.AllowedTools[externalName] || c.AllowedTools[name] {
		return true
	}

	// 3. Profile-based defaults (Using Internal Names)
	switch c.Profile {
	case ProfileOracle:
		// Oracle starts with ONLY "ask_specialist"
		if name == "agent.specialist" {
			return true
		}
		return false

	case ProfileDynamic:
		// Dynamic starts with ONLY "ask_the_master_gopher"
		if name == "agent.master" {
			return true
		}
		return false

	case ProfileFull:
		// Full profile enables everything by default
		return true

	case ProfileStandard:
		// Standard set
		switch name {
		case "file.outline", "symbol.inspect", "file.edit", "go.docs", "go.build", "go.test", "file.list", "project.map", "file.read":
			return true
		default:
			// Experimental tools are disabled in standard profile unless explicitly allowed
			return !experimental
		}

	default:
		return false
	}
}

// EnableExperimentalFeatures returns true if the profile supports experimental features.
// This is a helper for legacy checks.
func (c *Config) EnableExperimentalFeatures() bool {
	return c.Profile == ProfileFull
}
