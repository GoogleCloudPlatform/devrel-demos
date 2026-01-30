package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

type ControlRequest struct {
	Command string `json:"command"` // "stop"
}

type StartExperimentRequest struct {
	Name         string   `json:"name"`
	TemplateID   string   `json:"template_id"`
	Reps         int      `json:"reps"`
	Concurrent   int      `json:"concurrent"`
	Control      string   `json:"control"`
	Timeout      string   `json:"timeout"`
	Alternatives []string `json:"alternatives"`
	Scenarios    []string `json:"scenarios"`
}

func (api *API) ListExperiments(r *http.Request) (any, error) {
	return api.DB.GetExperiments()
}

func (api *API) DeleteAllExperiments(r *http.Request) (any, error) {
	// 1. Fetch all experiments to iterate
	exps, err := api.DB.GetExperiments()
	if err != nil {
		return nil, err
	}

	deletedCount := 0
	for _, e := range exps {
		if e.IsLocked {
			continue // Skip locked experiments
		}

		// Re-fetch full experiment details to ensure we have timestamp/name for directory resolution
		// (GetExperiments returns summary, but usually has enough, but let's be safe if GetExperiments changes)
		// Actually GetExperiments struct has Name and Timestamp, so we can use `e` directly if it matches models.Experiment.
		// However, let's use the helper which expects *models.Experiment.

		if err := api.deleteExperiment(&e); err != nil {
			log.Printf("Failed to delete experiment %d: %v", e.ID, err)
			// Continue deleting others
		} else {
			deletedCount++
		}
	}

	return map[string]string{"message": fmt.Sprintf("Deleted %d unlocked experiments", deletedCount)}, nil
}

func (api *API) GetExperiment(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}
	return api.DB.GetExperimentByID(id)
}

func (api *API) DeleteExperiment(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}

	// 1. Get experiment details
	exp, err := api.DB.GetExperimentByID(id)
	if err != nil {
		return nil, err
	}

	// 2. Check Lock
	if exp.IsLocked {
		return nil, NewAPIError(http.StatusBadRequest, "Experiment is locked and cannot be deleted")
	}

	// 3. Perform Deletion
	if err := api.deleteExperiment(exp); err != nil {
		return nil, err
	}

	return map[string]string{"message": "Experiment deleted"}, nil
}

// deleteExperiment performs the actual file and DB deletion for a single experiment
func (api *API) deleteExperiment(exp *models.Experiment) error {
	// 1. Delete files on disk
	cwd, _ := os.Getwd()
	dir, err := workspace.FindExperimentDir(cwd, exp.Timestamp, exp.Name)
	if err == nil && dir != "" {
		if err := os.RemoveAll(dir); err != nil {
			log.Printf("Failed to remove experiment directory %s: %v", dir, err)
		} else {
			log.Printf("Deleted experiment directory: %s", dir)
		}
	} else {
		// Just log context, if it didn't exist that's fine
		log.Printf("Experiment directory check for %s (ID %d): %v", exp.Name, exp.ID, err)
	}

	// 2. Delete from DB
	return api.DB.DeleteExperiment(exp.ID)
}

func (api *API) StartExperiment(r *http.Request) (any, error) {
	var req StartExperimentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	cwd, _ := os.Getwd()
	configPath := filepath.Join(cwd, "experiments", "templates", req.TemplateID, "config.yaml")
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		return nil, NewAPIError(http.StatusNotFound, fmt.Sprintf("Template config not found at %s", configPath))
	}

	// Create Experiment Record synchronously to ensure visibility in UI
	configContent, err := os.ReadFile(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	expRecord := &models.Experiment{
		Timestamp:         time.Now(),
		Name:              req.Name,
		ConfigPath:        configPath,                 // Could vary if RunExperiment relocates it
		Status:            db.ExperimentStatusRunning, // Mark as Running (or Starting)
		Reps:              req.Reps,
		Concurrent:        req.Concurrent,
		ConfigContent:     string(configContent),
		ExperimentControl: req.Control,
	}

	id, err := api.DB.CreateExperiment(expRecord)
	if err != nil {
		return nil, fmt.Errorf("failed to create experiment record: %w", err)
	}

	args := []string{
		"-config", configPath,
		"-reps", strconv.Itoa(req.Reps),
		"-concurrent", strconv.Itoa(req.Concurrent),
		"-start-experiment-id", strconv.FormatInt(id, 10),
	}
	if req.Name != "" {
		args = append(args, "-name", req.Name)
	}
	if req.Control != "" {
		args = append(args, "-control", req.Control)
	}
	if req.Timeout != "" {
		args = append(args, "-timeout", req.Timeout)
	}
	if len(req.Alternatives) > 0 {
		args = append(args, "-alternatives", strings.Join(req.Alternatives, ","))
	}
	if len(req.Scenarios) > 0 {
		args = append(args, "-scenarios", strings.Join(req.Scenarios, ","))
	}

	pid, err := spawnRunner(args)
	if err != nil {
		api.DB.UpdateExperimentStatus(id, db.ExperimentStatusAborted)
		api.DB.UpdateExperimentError(id, fmt.Sprintf("Failed to spawn runner: %v", err))
		return nil, fmt.Errorf("failed to spawn runner: %w", err)
	}

	// Update PID in DB if possible, or leave it.
	// Return ID so frontend can redirect immediately
	return map[string]string{"message": "Experiment started", "pid": strconv.Itoa(pid), "id": strconv.FormatInt(id, 10)}, nil
}

func (api *API) ControlExperiment(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}
	var req ControlRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}
	if err := api.DB.UpdateExecutionControl(id, req.Command); err != nil {
		return nil, err
	}
	return map[string]string{"status": "updated"}, nil
}

func (api *API) RelaunchExperiment(r *http.Request) (any, error) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}

	exp, err := api.DB.GetExperimentByID(id)
	if err != nil {
		return nil, err
	}

	if exp.ConfigPath == "" {
		return nil, NewAPIError(http.StatusBadRequest, "Experiment has no config path and cannot be relaunched")
	}

	// Spawning a new tenkai process with the original config
	args := []string{"-config", exp.ConfigPath}
	if exp.Name != "" {
		args = append(args, "-name", exp.Name+" (Relaunch)")
	}

	pid, err := spawnRunner(args)
	if err != nil {
		return nil, fmt.Errorf("failed to relaunch runner: %w", err)
	}

	return map[string]string{"message": "Experiment relaunched", "pid": strconv.Itoa(pid)}, nil
}

func (api *API) HandleExportReport(w http.ResponseWriter, r *http.Request) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		http.Error(w, "Invalid ID", http.StatusBadRequest)
		return
	}

	exp, err := api.DB.GetExperimentByID(id)
	if err != nil {
		http.Error(w, "Not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "text/markdown")
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"report-%d.md\"", id))
	w.Write([]byte(exp.ReportContent))
}

func (api *API) SaveAIAnalysis(r *http.Request) (any, error) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}

	var req struct {
		Analysis string `json:"analysis"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	if err := api.DB.UpdateExperimentAIAnalysis(id, req.Analysis); err != nil {
		return nil, err
	}

	return map[string]string{"status": "saved"}, nil
}

func (api *API) SaveExperimentAnnotations(r *http.Request) (any, error) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}

	var req struct {
		Annotations string `json:"annotations"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	if err := api.DB.UpdateExperimentAnnotations(id, req.Annotations); err != nil {
		return nil, err
	}

	return map[string]string{"status": "saved"}, nil
}

func spawnRunner(args []string) (int, error) {
	log.Printf("[Server] Spawning tenkai: %v", args)

	exe, err := os.Executable()
	if err != nil {
		exe = "tenkai"
	}
	cwd, _ := os.Getwd()
	cmd := exec.Command(exe, args...)
	cmd.Dir = cwd

	// Open tenkai.log for appending runner logs
	logPath := filepath.Join(cwd, "tenkai.log")
	if os.Getenv("K_SERVICE") != "" {
		logPath = "/tmp/tenkai.log"
	}

	f, err := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		log.Printf("[Server] Failed to open tenkai.log at %s: %v", logPath, err)
	}

	var multiOut, multiErr io.Writer
	var runnerOut, runnerErr bytes.Buffer

	// We pipe to:
	// 1. In-memory buffer (for final exit log)
	// 2. tenkai.log file (for UI)
	// 3. os.Stdout/Stderr (for real-time terminal output, as requested)

	writersOut := []io.Writer{&runnerOut, os.Stdout}
	writersErr := []io.Writer{&runnerErr, os.Stderr}

	if f != nil {
		writersOut = append(writersOut, f)
		writersErr = append(writersErr, f)
	}

	multiOut = io.MultiWriter(writersOut...)
	multiErr = io.MultiWriter(writersErr...)

	cmd.Stdout = multiOut
	cmd.Stderr = multiErr

	if err := cmd.Start(); err != nil {
		if f != nil {
			f.Close()
		}
		return 0, err
	}

	go func() {
		if f != nil {
			defer f.Close()
		}
		if err := cmd.Wait(); err != nil {
			log.Printf("[Server] Runner process %d exited with error: %v", cmd.Process.Pid, err)
			// We already streamed to log file, so maybe don't need to dump big blobs to server log?
			// But let's keep it for now as it goes to stdout of this process.
			log.Printf("[Server] Runner Stderr: %s", runnerErr.String())
		} else {
			log.Printf("[Server] Runner process %d finished successfully", cmd.Process.Pid)
		}
	}()

	return cmd.Process.Pid, nil
}

func (api *API) FixDB(r *http.Request) (any, error) {
	if err := api.DB.FixSequences(); err != nil {
		return nil, err
	}
	return map[string]string{"status": "fixed sequences"}, nil
}
