package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"gopkg.in/yaml.v3"
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
	dir, err := api.WSMgr.FindExperimentDir(exp.Timestamp, exp.Name)
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

	log.Printf("[Server] Starting experiment %s from template %s", req.Name, req.TemplateID)

	tmpl, err := api.WSMgr.GetTemplate(req.TemplateID)
	if err != nil {
		log.Printf("[Server] Template config NOT found for ID %s: %v", req.TemplateID, err)
		return nil, NewAPIError(http.StatusNotFound, fmt.Sprintf("Template config not found: %v", err))
	}

	configContent := tmpl.ConfigContent
	configPath := tmpl.Path

	expRecord := &models.Experiment{
		Timestamp:         time.Now(),
		Name:              req.Name,
		ConfigPath:        configPath,                 // Could vary if RunExperiment relocates it
		Status:            db.ExperimentStatusRunning, // Mark as Running (or Starting)
		Reps:              req.Reps,
		Concurrent:        req.Concurrent,
		ConfigContent:     configContent,
		ExperimentControl: req.Control,
	}

	id, err := api.DB.CreateExperiment(expRecord)
	if err != nil {
		return nil, fmt.Errorf("failed to create experiment record: %w", err)
	}

	// Load Configuration for Runner
	var cfg config.Configuration
	if err := yaml.Unmarshal([]byte(configContent), &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config: %w", err)
	}

	// Apply overrides from request
	cfg.Name = req.Name
	cfg.Repetitions = req.Reps
	cfg.MaxConcurrent = req.Concurrent
	cfg.Control = req.Control
	cfg.Timeout = req.Timeout
	if len(req.Alternatives) > 0 {

		var filteredAlts []config.Alternative
		for _, name := range req.Alternatives {
			for _, a := range cfg.Alternatives {
				if a.Name == name {
					filteredAlts = append(filteredAlts, a)
					break
				}
			}
		}
		cfg.Alternatives = filteredAlts
	}
	if len(req.Scenarios) > 0 {
		cfg.Scenarios = req.Scenarios
	}

	// Trigger Orchestration in background
	go func() {
		defer func() {
			if r := recover(); r != nil {
				log.Printf("[Server] CRITICAL PANIC in experiment orchestration (ID %d): %v", id, r)
				api.DB.UpdateExperimentStatus(id, db.ExperimentStatusAborted)
				api.DB.UpdateExperimentError(id, fmt.Sprintf("Server panic: %v", r))
			}
		}()
		if err := api.Runner.RunExperiment(context.Background(), &cfg, id); err != nil {
			log.Printf("[Server] Orchestration failed for experiment %d: %v", id, err)
			api.DB.UpdateExperimentStatus(id, db.ExperimentStatusAborted)
			api.DB.UpdateExperimentError(id, err.Error())
		}
	}()

	// Return ID so frontend can redirect immediately
	return map[string]string{"message": "Experiment started", "id": strconv.FormatInt(id, 10)}, nil
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

	if exp.ConfigContent == "" {
		return nil, NewAPIError(http.StatusBadRequest, "Experiment has no config content and cannot be relaunched")
	}

	// Parse Configuration for Runner
	var cfg config.Configuration
	if err := yaml.Unmarshal([]byte(exp.ConfigContent), &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse experiment config: %w", err)
	}
	cfg.Name = exp.Name + " (Relaunch)"

	// Create NEW Experiment record for relaunch
	newExp := &models.Experiment{
		Timestamp:         time.Now(),
		Name:              exp.Name + " (Relaunch)",
		ConfigPath:        exp.ConfigPath,
		Status:            db.ExperimentStatusRunning,
		Reps:              cfg.Repetitions, // Use original config value
		Concurrent:        cfg.MaxConcurrent,
		ConfigContent:     exp.ConfigContent,
		ExperimentControl: exp.ExperimentControl,
	}

	newID, err := api.DB.CreateExperiment(newExp)
	if err != nil {
		return nil, fmt.Errorf("failed to create experiment record: %w", err)
	}

	// Trigger Orchestration in background with NEW ID
	go func() {
		defer func() {
			if r := recover(); r != nil {
				log.Printf("[Server] CRITICAL PANIC in experiment orchestration (ID %d): %v", newID, r)
				api.DB.UpdateExperimentStatus(newID, db.ExperimentStatusAborted)
				api.DB.UpdateExperimentError(newID, fmt.Sprintf("Server panic: %v", r))
			}
		}()
		if err := api.Runner.RunExperiment(context.Background(), &cfg, newID); err != nil {
			log.Printf("[Server] Orchestration failed for relaunch experiment %d: %v", newID, err)
			api.DB.UpdateExperimentStatus(newID, db.ExperimentStatusAborted)
			api.DB.UpdateExperimentError(newID, err.Error())
		}
	}()

	return map[string]string{"message": "Experiment relaunched", "id": strconv.FormatInt(newID, 10)}, nil
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

func (api *API) FixDB(r *http.Request) (any, error) {

	if err := api.DB.FixSequences(); err != nil {
		return nil, err
	}
	return map[string]string{"status": "fixed sequences"}, nil
}
