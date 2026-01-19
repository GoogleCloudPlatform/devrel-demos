// Package config handles configuration loading for the application.
package config

import (
	"flag"
	"strings"
)

// Config holds the application configuration.
type Config struct {
	ListenAddr    string
	Version       bool
	Agents        bool
	ListTools     bool // List available tools for the selected profile and exit
	DefaultModel  string
	AllowedTools  map[string]bool // If non-empty, ONLY these tools are allowed
	DisabledTools map[string]bool // These tools are explicitly disabled
}

// Load parses command-line arguments and returns a Config struct.
func Load(args []string) (*Config, error) {
	fs := flag.NewFlagSet("godoctor", flag.ContinueOnError)
	versionFlag := fs.Bool("version", false, "print the version and exit")
	agentsFlag := fs.Bool("agents", false, "print LLM agent instructions and exit")
	listToolsFlag := fs.Bool("list-tools", false, "list available tools and exit")
	listenAddr := fs.String("listen", "", "listen address for HTTP transport (e.g., :8080)")
	defaultModel := fs.String("model", "gemini-2.5-pro", "default Gemini model to use")
	allowFlag := fs.String("allow", "", "comma-separated list of tools to explicitly allow")
	disableFlag := fs.String("disable", "", "comma-separated list of tools to disable")

	if err := fs.Parse(args); err != nil {
		return nil, err
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
		AllowedTools:  parseList(*allowFlag),
		DisabledTools: parseList(*disableFlag),
	}

	return cfg, nil
}

// IsToolEnabled checks if a tool should be enabled.
func (c *Config) IsToolEnabled(name string) bool {
	// 1. Explicitly Disabled
	if c.DisabledTools[name] {
		return false
	}

	// 2. Explicitly Allowed (Whitelist mode)
	if len(c.AllowedTools) > 0 {
		return c.AllowedTools[name]
	}

	// 3. Default: All enabled
	return true
}
