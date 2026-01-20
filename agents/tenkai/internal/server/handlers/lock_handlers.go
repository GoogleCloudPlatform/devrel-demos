package handlers

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"gopkg.in/yaml.v3"
)

func (api *API) HandleExperimentLock(r *http.Request) (any, error) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid experiment ID")
	}

	var req struct {
		Locked bool `json:"locked"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	if err := api.DB.ToggleExperimentLock(id, req.Locked); err != nil {
		return nil, fmt.Errorf("failed to update experiment lock: %w", err)
	}

	return map[string]any{"id": id, "is_locked": req.Locked}, nil
}

func (api *API) HandleScenarioLock(r *http.Request) (any, error) {
	id := r.PathValue("id")

	var req struct {
		Locked bool `json:"locked"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	// Scenarios are file-based (scenario.yaml)
	scen, err := api.WSMgr.GetScenario(id)
	if err != nil {
		return nil, NewAPIError(http.StatusNotFound, err.Error())
	}

	configPath := filepath.Join(scen.Path, "scenario.yaml")
	cfg, err := config.LoadScenarioConfig(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to load scenario config: %w", err)
	}

	cfg.IsLocked = req.Locked

	data, err := yaml.Marshal(cfg)
	if err != nil {
		return nil, err
	}

	if err := os.WriteFile(configPath, data, 0644); err != nil {
		return nil, err
	}

	return map[string]any{"id": id, "is_locked": req.Locked}, nil
}

func (api *API) HandleTemplateLock(r *http.Request) (any, error) {
	id := r.PathValue("id")

	var req struct {
		Locked bool `json:"locked"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	// Templates are file-based (config.yaml)
	templatesBase := filepath.Join(api.WSMgr.BasePath, "experiments", "templates")
	configPath := filepath.Join(templatesBase, id, "config.yaml")

	cfg, err := config.Load(configPath)
	if err != nil {
		return nil, NewAPIError(http.StatusNotFound, err.Error())
	}

	cfg.IsLocked = req.Locked

	data, err := yaml.Marshal(cfg)
	if err != nil {
		return nil, err
	}

	if err := os.WriteFile(configPath, data, 0644); err != nil {
		return nil, err
	}

	return map[string]any{"id": id, "is_locked": req.Locked}, nil
}
