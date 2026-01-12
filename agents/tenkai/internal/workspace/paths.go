package workspace

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// GetExperimentFolderName returns the standard folder name for an experiment.
func GetExperimentFolderName(timestamp time.Time, name string) string {
	tsStr := timestamp.Format("20060102-150405")
	if name == "" {
		return tsStr
	}
	return fmt.Sprintf("%s_%s", tsStr, name)
}

// FindExperimentDir locates the physical directory for an experiment.
// It tries an exact match for the expected folder name first, then falls back to prefix matching.
func FindExperimentDir(cwd string, timestamp time.Time, name string) (string, error) {
	base := filepath.Join(cwd, "experiments", ".runs")
	entries, err := os.ReadDir(base)
	if err != nil {
		return "", err
	}

	expectedName := GetExperimentFolderName(timestamp, name)
	tsPrefix := timestamp.Format("20060102-150405")

	// Try exact match first
	for _, e := range entries {
		if e.IsDir() && e.Name() == expectedName {
			return filepath.Join(base, e.Name()), nil
		}
	}

	// Fallback to prefix match for compatibility
	for _, e := range entries {
		if e.IsDir() && strings.HasPrefix(e.Name(), tsPrefix) {
			return filepath.Join(base, e.Name()), nil
		}
	}

	return "", fmt.Errorf("experiment directory not found (expected: %s, prefix: %s) in %s", expectedName, tsPrefix, base)
}
