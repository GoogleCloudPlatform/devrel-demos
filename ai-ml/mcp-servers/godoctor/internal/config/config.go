// Package config handles configuration loading for the application.
package config

import (
	"flag"
	"fmt"
	"strings"

	"github.com/danicat/godoctor/internal/toolnames"
)

// Profile defines the operating mode of the server.
type Profile string

const (
	ProfileStandard Profile = "standard"
	ProfileAdvanced Profile = "advanced"
	ProfileOracle   Profile = "oracle"
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
	listenAddr := fs.String("listen", "", "listen address for HTTP transport (e.g., :8080)")
	defaultModel := fs.String("model", "gemini-2.5-pro", "default Gemini model to use")
	profileFlag := fs.String("profile", "standard", "server profile: standard, advanced, oracle")
	allowFlag := fs.String("allow", "", "comma-separated list of tools to explicitly allow (overrides profile defaults)")
	disableFlag := fs.String("disable", "", "comma-separated list of tools to disable")

	// Legacy flag for backward compatibility, mapped to "full" profile conceptually or ignored if profile is set
	experimentalFlag := fs.Bool("experimental", false, "[deprecated] enable experimental features (use --profile=advanced)")

	if err := fs.Parse(args); err != nil {
		return nil, err
	}

	profile := Profile(*profileFlag)
	if *experimentalFlag && profile == ProfileStandard {
		profile = ProfileAdvanced
	}

	switch profile {
	case ProfileStandard, ProfileAdvanced, ProfileOracle:
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
	if c.Profile == ProfileAdvanced {
		return true
	}

	profileDef, ok := toolnames.ActiveProfiles[string(c.Profile)]
	if !ok {
		return false
	}

	for _, t := range profileDef.Tools {
		if t == name {
			return true
		}
	}

	return false
}

// EnableExperimentalFeatures returns true if the profile supports experimental features.
// This is a helper for legacy checks.
func (c *Config) EnableExperimentalFeatures() bool {
	return c.Profile == ProfileAdvanced
}
