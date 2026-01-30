package handlers

import (
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
)

func (api *API) HandleHealth(r *http.Request) (any, error) {
	return map[string]string{"status": "ok"}, nil
}

func (api *API) HandleGlobalStats(r *http.Request) (any, error) {
	return api.DB.GetGlobalStats()
}

func (api *API) HandleLogs(r *http.Request) (any, error) {
	// Determine log path based on environment
	cwd, _ := os.Getwd()
	logPath := filepath.Join(cwd, "tenkai.log")

	if os.Getenv("K_SERVICE") != "" {
		logPath = "/tmp/tenkai.log"
	}

	if _, err := os.Stat(logPath); os.IsNotExist(err) {
		return map[string]string{"logs": fmt.Sprintf("(No logs found at %s)", logPath)}, nil
	}

	// Read last 1000 lines
	cmd := exec.Command("tail", "-n", "1000", logPath)
	out, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to read logs: %w", err)
	}

	return map[string]string{"logs": string(out)}, nil
}
