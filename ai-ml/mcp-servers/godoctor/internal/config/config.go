// Package config handles configuration loading for the application.
package config

import (
	"flag"
	"fmt"
	"strings"
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
	if c.DisabledTools[name] {
		return false
	}

	// 2. Explicitly Allowed?
	if c.AllowedTools[name] {
		return true
	}

	// 3. Profile-based defaults
	switch c.Profile {
	case ProfileOracle:
		// Oracle starts with ONLY "ask_specialist" (and maybe "list_files" for context)
		// Everything else must be explicitly allowed by the oracle via UpdateTools
		if name == "ask_specialist" {
			return true
		}
		return false

	case ProfileDynamic:
		// Dynamic starts with ONLY "ask_the_master_gopher"
		if name == "ask_the_master_gopher" {
			return true
		}
		return false

	case ProfileFull:
		// Full profile enables everything by default
		return true

	case ProfileStandard:
		// Standard set
		switch name {
		case "code_outline", "inspect_symbol", "smart_edit", "read_docs", "go_build", "go_test", "list_files":
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
