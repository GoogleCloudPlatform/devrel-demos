package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
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
	if err := api.DB.DeleteAllExperiments(); err != nil {
		return nil, err
	}
	return map[string]string{"message": "All experiments deleted"}, nil
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
	if err := api.DB.DeleteExperiment(id); err != nil {
		return nil, err
	}
	return map[string]string{"message": "Experiment deleted"}, nil
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

	args := []string{
		"-config", configPath,
		"-reps", strconv.Itoa(req.Reps),
		"-concurrent", strconv.Itoa(req.Concurrent),
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
		return nil, fmt.Errorf("failed to spawn runner: %w", err)
	}

	return map[string]string{"message": "Experiment started", "pid": strconv.Itoa(pid)}, nil
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

func spawnRunner(args []string) (int, error) {
	log.Printf("[Server] Spawning tenkai: %v", args)

	exe, err := os.Executable()
	if err != nil {
		exe = "tenkai"
	}
	cwd, _ := os.Getwd()
	cmd := exec.Command(exe, args...)
	cmd.Dir = cwd
	cmd.Env = os.Environ()

	// Capture stdout/stderr for debugging runner failures
	// Note: We're creating buffers but they live in the goroutine closure if referenced there?
	// Actually capturing to local buffers specific to this function call context
	// We need to manage lifecycle. Simple logging goroutine is fine.
	// But `bytes.Buffer` is not thread safe if we were reading it elsewhere. Here we just print it at the end.

	// To capture logs properly, we should stream them to the main log or a file, but for now logging to server log on exit is what was there.
	// We'll replicate the existing behavior safely.
	var runnerOut, runnerErr bytes.Buffer
	cmd.Stdout = &runnerOut
	cmd.Stderr = &runnerErr

	if err := cmd.Start(); err != nil {
		return 0, err
	}

	go func() {
		if err := cmd.Wait(); err != nil {
			log.Printf("[Server] Runner process %d exited with error: %v", cmd.Process.Pid, err)
			log.Printf("[Server] Runner Stderr: %s", runnerErr.String())
			log.Printf("[Server] Runner Stdout: %s", runnerOut.String())
		} else {
			log.Printf("[Server] Runner process %d finished successfully", cmd.Process.Pid)
		}
	}()

	return cmd.Process.Pid, nil
}
