package handlers

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
)

func (api *API) ListScenarios(r *http.Request) (any, error) {
	return api.WSMgr.ListScenarios(), nil
}

func (api *API) CreateScenario(r *http.Request) (any, error) {
	if err := r.ParseMultipartForm(32 << 20); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Failed to parse form")
	}
	name := r.FormValue("name")
	desc := r.FormValue("description")
	task := r.FormValue("prompt")

	var assets []config.Asset
	assetType := r.FormValue("asset_type")

	if assetType == "folder" || assetType == "files" {
		files := r.MultipartForm.File["files"]
		for _, fileHeader := range files {
			f, err := fileHeader.Open()
			if err != nil {
				return nil, fmt.Errorf("failed to open uploaded file: %w", err)
			}
			content, err := io.ReadAll(f)
			f.Close()
			if err != nil {
				return nil, fmt.Errorf("failed to read uploaded file: %w", err)
			}

			// Use Filename as target. Browser might send relative path in Filename if webkitdirectory used?
			// Usually Filename is just basename unless standardized.
			// But for single files it's basename.
			assets = append(assets, config.Asset{
				Type:    "file",
				Target:  fileHeader.Filename,
				Content: string(content),
			})
		}
	} else if assetType == "create" {
		assets = append(assets, config.Asset{
			Type:    "file",
			Target:  r.FormValue("file_name"),
			Content: r.FormValue("file_content"),
		})
	} else if assetType == "git" {
		assets = append(assets, config.Asset{
			Type:   "git",
			Source: r.FormValue("git_url"),
			Ref:    r.FormValue("git_ref"),
			Target: ".",
		})
	}

	var validation []config.ValidationRule
	valJSON := r.FormValue("validation")
	if valJSON != "" {
		if err := json.Unmarshal([]byte(valJSON), &validation); err != nil {
			return nil, NewAPIError(http.StatusBadRequest, fmt.Sprintf("Invalid validation JSON: %v", err))
		}
	}

	id, err := api.WSMgr.CreateScenario(name, desc, task, assets, validation)
	if err != nil {
		return nil, err
	}
	return map[string]string{"id": id, "name": name}, nil
}

func (api *API) GetScenario(r *http.Request) (any, error) {
	id := r.PathValue("id")
	return api.WSMgr.GetScenario(id)
}

func (api *API) UpdateScenario(r *http.Request) (any, error) {
	id := r.PathValue("id")
	var req struct {
		Name        string                  `json:"name"`
		Description string                  `json:"description"`
		Task        string                  `json:"task"`
		Validation  []config.ValidationRule `json:"validation"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	if err := api.WSMgr.UpdateScenario(id, req.Name, req.Description, req.Task, req.Validation); err != nil {
		if strings.Contains(err.Error(), "not found") {
			return nil, NewAPIError(http.StatusNotFound, err.Error())
		}
		return nil, err
	}

	return map[string]string{"status": "updated"}, nil
}

func (api *API) DeleteScenario(r *http.Request) (any, error) {
	id := r.PathValue("id")
	if err := api.WSMgr.DeleteScenario(id); err != nil {
		if strings.Contains(err.Error(), "not found") {
			return nil, NewAPIError(http.StatusNotFound, err.Error())
		}
		return nil, err
	}
	return map[string]string{"status": "deleted"}, nil
}
