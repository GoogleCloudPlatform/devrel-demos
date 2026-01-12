package handlers

import (
	"bytes"
	"encoding/json"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func TestListTemplates(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	api.WSMgr.CreateTemplate("T1", "D1", "config: 1", nil)
	api.WSMgr.CreateTemplate("T2", "D2", "config: 2", nil)

	req := httptest.NewRequest("GET", "/api/templates", nil)
	res, err := api.ListTemplates(req)
	if err != nil {
		t.Fatalf("Handler returned error: %v", err)
	}

	tmpls, ok := res.([]workspace.Template)
	if !ok {
		t.Fatalf("Expected []workspace.Template, got %T", res)
	}
	if len(tmpls) != 2 {
		t.Errorf("Expected 2 templates, got %d", len(tmpls))
	}
}

func TestCreateTemplate(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	reqBody := map[string]interface{}{
		"name":         "New Tmpl",
		"description":  "Desc",
		"yaml_content": "name: test",
		"files":        map[string]string{"foo": "bar"},
	}
	jsonBody, _ := json.Marshal(reqBody)

	req := httptest.NewRequest("POST", "/api/templates", bytes.NewBuffer(jsonBody))
	res, err := api.CreateTemplate(req)
	if err != nil {
		t.Fatalf("Handler returned error: %v", err)
	}

	resMap, ok := res.(map[string]string)
	if !ok {
		t.Fatalf("Expected map[string]string, got %T", res)
	}
	if resMap["name"] != "New Tmpl" {
		t.Errorf("Expected name 'New Tmpl', got '%s'", resMap["name"])
	}
}

func TestDeleteTemplate(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	id, _ := api.WSMgr.CreateTemplate("T1", "D1", "c: 1", nil)

	req := httptest.NewRequest("DELETE", "/api/templates/"+id, nil)
	req.SetPathValue("id", id)

	res, err := api.DeleteTemplate(req)
	if err != nil {
		t.Fatalf("Handler returned error: %v", err)
	}

	resMap, ok := res.(map[string]string)
	if !ok {
		t.Fatalf("Expected map[string]string, got %T", res)
	}
	if resMap["status"] != "deleted" {
		t.Errorf("Expected status deleted, got %s", resMap["status"])
	}
}
