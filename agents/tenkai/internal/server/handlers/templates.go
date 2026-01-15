package handlers

import (
	"encoding/json"
	"log"
	"net/http"
	"strings"

	"gopkg.in/yaml.v3"
)

func (api *API) ListTemplates(r *http.Request) (any, error) {
	return api.WSMgr.ListTemplates(), nil
}

func (api *API) CreateTemplate(r *http.Request) (any, error) {
	var req struct {
		Name        string            `json:"name"`
		Description string            `json:"description"`
		Config      string            `json:"yaml_content"`
		Files       map[string]string `json:"files"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}
	id, err := api.WSMgr.CreateTemplate(req.Name, req.Description, req.Config, req.Files)
	if err != nil {
		return nil, err
	}
	return map[string]string{"id": id, "name": req.Name}, nil
}

func (api *API) GetTemplateConfig(r *http.Request) (any, error) {

	id := r.PathValue("id")
	tmpl, err := api.WSMgr.GetTemplate(id)
	if err != nil {
		return nil, NewAPIError(http.StatusNotFound, err.Error())
	}

	var cfgMap map[string]interface{}
	if err := yaml.Unmarshal([]byte(tmpl.ConfigContent), &cfgMap); err != nil {
		log.Printf("Warning: failed to parse config YAML: %v", err)
	}

	return map[string]interface{}{
		"name":    tmpl.Name,
		"content": tmpl.ConfigContent,
		"config":  cfgMap,
	}, nil
}

func (api *API) UpdateTemplate(r *http.Request) (any, error) {
	id := r.PathValue("id")
	var req struct {
		Config string            `json:"yaml_content"`
		Files  map[string]string `json:"files"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	if err := api.WSMgr.UpdateTemplate(id, req.Config, req.Files); err != nil {
		if strings.Contains(err.Error(), "not found") {
			return nil, NewAPIError(http.StatusNotFound, err.Error())
		}
		return nil, err
	}

	return map[string]string{"status": "updated"}, nil
}

func (api *API) DeleteTemplate(r *http.Request) (any, error) {
	id := r.PathValue("id")
	if err := api.WSMgr.DeleteTemplate(id); err != nil {
		if strings.Contains(err.Error(), "not found") {
			return nil, NewAPIError(http.StatusNotFound, err.Error())
		}
		return nil, err
	}
	return map[string]string{"status": "deleted"}, nil
}

func (api *API) DeleteAllTemplates(r *http.Request) (any, error) {
	if err := api.WSMgr.DeleteAllTemplates(); err != nil {
		return nil, err
	}
	return map[string]string{"status": "all deleted"}, nil
}
