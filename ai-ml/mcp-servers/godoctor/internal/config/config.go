// Package config handles configuration loading for the application.
package config

import (
	"flag"
)

// Config holds the application configuration.
type Config struct {
	ListenAddr   string
	Version      bool
	Agents       bool
	DefaultModel string
	Experimental bool
}

// Load parses command-line arguments and returns a Config struct.
func Load(args []string) (*Config, error) {
	fs := flag.NewFlagSet("godoctor", flag.ContinueOnError)
	versionFlag := fs.Bool("version", false, "print the version and exit")
	agentsFlag := fs.Bool("agents", false, "print LLM agent instructions and exit")
	listenAddr := fs.String("listen", "", "listen address for HTTP transport (e.g., :8080)")
	defaultModel := fs.String("model", "gemini-2.5-pro", "default Gemini model to use")
	experimentalFlag := fs.Bool("experimental", false, "enable experimental features")

	if err := fs.Parse(args); err != nil {
		return nil, err
	}

	cfg := &Config{
		ListenAddr:   *listenAddr,
		Version:      *versionFlag,
		Agents:       *agentsFlag,
		DefaultModel: *defaultModel,
		Experimental: *experimentalFlag,
	}

	return cfg, nil
}
