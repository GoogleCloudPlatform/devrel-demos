package handlers

import (
	"bytes"
	"encoding/json"
	"mime/multipart"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func TestListScenarios(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	// Seed via Workspace Manager
	api.WSMgr.CreateScenario("S1", "Desc1", "Task1", nil, nil)
	api.WSMgr.CreateScenario("S2", "Desc2", "Task2", nil, nil)

	req := httptest.NewRequest("GET", "/api/scenarios", nil)

	res, err := api.ListScenarios(req)
	if err != nil {
		t.Fatalf("Handler returned error: %v", err)
	}

	scens, ok := res.([]workspace.Scenario)
	if !ok {
		t.Fatalf("Expected []workspace.Scenario, got %T", res)
	}
	if len(scens) != 2 {
		t.Errorf("Expected 2 scenarios, got %d", len(scens))
	}
}

func TestCreateScenario(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	// Multipart Form
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	writer.WriteField("name", "New Scen")
	writer.WriteField("description", "Desc")
	writer.WriteField("prompt", "Task")
	writer.WriteField("asset_type", "none")
	writer.Close()

	req := httptest.NewRequest("POST", "/api/scenarios", body)
	req.Header.Set("Content-Type", writer.FormDataContentType())

	res, err := api.CreateScenario(req)
	if err != nil {
		t.Fatalf("Handler returned error: %v", err)
	}

	resMap, ok := res.(map[string]string)
	if !ok {
		t.Fatalf("Expected map[string]string, got %T", res)
	}
	if resMap["name"] != "New Scen" {
		t.Errorf("Expected name 'New Scen', got '%s'", resMap["name"])
	}
}

func TestUpdateScenario(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	id, _ := api.WSMgr.CreateScenario("Old Name", "Desc", "Task", nil, nil)

	reqBody := map[string]interface{}{
		"name":        "New Name",
		"description": "New Desc",
		"task":        "New Task",
		"validation":  []config.ValidationRule{},
	}
	jsonBody, _ := json.Marshal(reqBody)

	req := httptest.NewRequest("PUT", "/api/scenarios/"+id, bytes.NewBuffer(jsonBody))
	req.SetPathValue("id", id)

	res, err := api.UpdateScenario(req)
	if err != nil {
		t.Fatalf("Handler returned error: %v", err)
	}

	resMap, ok := res.(map[string]string)
	if !ok {
		t.Fatalf("Expected map[string]string, got %T", res)
	}
	if resMap["status"] != "updated" {
		t.Errorf("Expected status updated, got %s", resMap["status"])
	}

	// Verify
	scen, _ := api.WSMgr.GetScenario(id)
	if scen.Name != "New Name" {
		t.Errorf("Expected name 'New Name', got '%s'", scen.Name)
	}
}
