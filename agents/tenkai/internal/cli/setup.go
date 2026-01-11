package cli

import (
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"gopkg.in/yaml.v3"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
)

func setupLogging(cwd string) {
	logFilePath := filepath.Join(cwd, "tenkai.log")
	logFile, err := os.OpenFile(logFilePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err == nil {
		mw := io.MultiWriter(os.Stdout, logFile)
		log.SetOutput(mw)
	} else {
		fmt.Printf("Warning: failed to create tenkai.log: %v\n", err)
	}
}

func initDB(cwd string) (*db.DB, error) {
	dbPath := filepath.Join(cwd, "experiments", "tenkai.db")
	database, err := db.Open(dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}
	return database, nil
}

func loadAndOverrideConfig(flags Flags) (*config.Configuration, []string, error) {
	if *flags.ConfigPath == "" {
		return nil, nil, fmt.Errorf("config path is empty")
	}

	cfg, err := config.Load(*flags.ConfigPath)
	if err != nil {
		return nil, nil, err
	}

	var overrideNotes []string
	if *flags.Reps > 0 {
		if *flags.Reps != cfg.Repetitions {
			overrideNotes = append(overrideNotes, fmt.Sprintf("⚠️ Repetitions overridden to %d via CLI (config: %d)", *flags.Reps, cfg.Repetitions))
		}
		cfg.Repetitions = *flags.Reps
	}
	if *flags.Concurrent > 0 {
		if *flags.Concurrent != cfg.MaxConcurrent {
			overrideNotes = append(overrideNotes, fmt.Sprintf("⚠️ Max concurrent workers overridden to %d via CLI (config: %d)", *flags.Concurrent, cfg.MaxConcurrent))
		}
		cfg.MaxConcurrent = *flags.Concurrent
	}
	if *flags.Name != "" {
		cfg.Name = *flags.Name
	}
	if *flags.Control != "" {
		cfg.Control = *flags.Control
	}
	if *flags.Timeout != "" {
		if _, err := time.ParseDuration(*flags.Timeout); err != nil {
			return nil, nil, fmt.Errorf("invalid timeout format %q: %w", *flags.Timeout, err)
		}
		cfg.Timeout = *flags.Timeout
		overrideNotes = append(overrideNotes, fmt.Sprintf("⏱️ Timeout overridden to %s via CLI", *flags.Timeout))
	}

	applyFilters(cfg, flags, &overrideNotes)

	return cfg, overrideNotes, nil
}

func applyFilters(cfg *config.Configuration, flags Flags, notes *[]string) {
	if *flags.Alts != "" {
		alts := strings.Split(*flags.Alts, ",")
		var filtered []config.Alternative
		for _, name := range alts {
			name = strings.TrimSpace(name)
			for _, a := range cfg.Alternatives {
				if a.Name == name {
					filtered = append(filtered, a)
					break
				}
			}
		}
		if len(filtered) > 0 {
			if len(filtered) < len(cfg.Alternatives) {
				*notes = append(*notes, fmt.Sprintf("🎯 Alternatives filtered to: %s", *flags.Alts))
			}
			cfg.Alternatives = filtered
		}
	}

	if *flags.Scens != "" {
		scens := strings.Split(*flags.Scens, ",")
		var filtered []string
		for _, name := range scens {
			name = strings.TrimSpace(name)
			for _, s := range cfg.Scenarios {
				if s == name || filepath.Base(s) == name {
					filtered = append(filtered, s)
					break
				}
			}
		}
		if len(filtered) > 0 {
			if len(filtered) < len(cfg.Scenarios) {
				*notes = append(*notes, fmt.Sprintf("🎯 Scenarios filtered to: %s", *flags.Scens))
			}
			cfg.Scenarios = filtered
		}
	}
}

func prepareExperimentDir(cwd string, cfg *config.Configuration, timestamp time.Time) (string, string, error) {
	tsStr := timestamp.Format("20060102-150405")
	folderName := tsStr
	if cfg.Name != "" {
		folderName = fmt.Sprintf("%s_%s", tsStr, cfg.Name)
	}

	experimentDir := filepath.Join(cwd, "experiments", "runs", folderName)
	if err := os.MkdirAll(experimentDir, 0755); err != nil {
		return "", "", err
	}

	effectiveConfigData, err := yaml.Marshal(cfg)
	if err != nil {
		return "", "", err
	}

	destConfigPath := filepath.Join(experimentDir, "config.yaml")
	if err := os.WriteFile(destConfigPath, effectiveConfigData, 0644); err != nil {
		log.Printf("Warning: failed to write config file: %v", err)
	} else {
		fmt.Printf("Configuration saved to: %s\n", destConfigPath)
	}
	return experimentDir, destConfigPath, nil
}
