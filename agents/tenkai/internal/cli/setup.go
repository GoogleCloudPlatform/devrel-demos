package cli

import (
	"fmt"
	"io"
	"log"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"time"

	"gopkg.in/yaml.v3"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func SetupLogging(cwd string) {
	logPath := filepath.Join(cwd, "tenkai.log")

	// Cloud Run Environment
	inCloud := os.Getenv("K_SERVICE") != ""
	if inCloud {
		logPath = "/tmp/tenkai.log"
	}

	logFile, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		fmt.Printf("Warning: failed to create log file at %s: %v\n", logPath, err)
		return
	}

	var mw io.Writer
	if inCloud {
		// Cloud: Stderr (for GCP) + File (for UI)
		mw = io.MultiWriter(os.Stderr, logFile)

		// Use JSON for Cloud structured logging, but it will also go to the file.
		// Use TextHandler if we prefer readability in UI, but JSON is better for Cloud Logging.
		// Let's stick to Text for now to ensure the UI is readable as requested.
		// Actually, let's use JSON handler because Cloud Logging really prefers it for severity.
		// The UI will show JSON lines, which is acceptable.
		logger := slog.New(slog.NewJSONHandler(mw, nil))
		slog.SetDefault(logger)
	} else {
		// Local: Stdout + File
		mw = io.MultiWriter(os.Stdout, logFile)
	}

	// Capture standard log output as well
	log.SetOutput(mw)
}

func InitDB(cwd string) (*db.DB, error) {
	// Check for Env Vars for Cloud SQL / Postgres
	driver := os.Getenv("DB_DRIVER")
	dsn := os.Getenv("DB_DSN")

	if driver == "" {
		driver = "sqlite"
		dsn = filepath.Join(cwd, "experiments", "tenkai.db")
		// In Cloud Run, the app directory is read-only.
		// If using SQLite (default), we must use /tmp.
		if os.Getenv("K_SERVICE") != "" {
			dsn = "/tmp/tenkai.db"
			fmt.Printf("Notice: Running in Cloud Run with SQLite. Using ephemeral DB at %s\n", dsn)
		}
	}

	database, err := db.Open(driver, dsn)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}
	return database, nil
}

func LoadAndOverrideConfig(flags Flags) (*config.Configuration, []string, error) {
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
		var finalScenarios []string
		for _, name := range scens {
			name = strings.TrimSpace(name)
			if name != "" {
				finalScenarios = append(finalScenarios, name)
			}
		}
		if len(finalScenarios) > 0 {
			cfg.Scenarios = finalScenarios
			*notes = append(*notes, fmt.Sprintf("🎯 Scenarios set to: %s", *flags.Scens))
		}
	}
}

func prepareExperimentDir(cwd string, cfg *config.Configuration, timestamp time.Time) (string, string, error) {
	folderName := workspace.GetExperimentFolderName(timestamp, cfg.Name)

	experimentDir := filepath.Join(cwd, "experiments", ".runs", folderName)
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
