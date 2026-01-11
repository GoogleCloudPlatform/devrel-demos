package handlers

import (
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
)

func TestListExperiments(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	// Seed
	createTestExperiment(t, api, "Exp 1")
	createTestExperiment(t, api, "Exp 2")

	// Call Handler directly
	// Note: Our handlers have signature (r *http.Request) (any, error)
	// We can test them without the full HTTP server wrap if we trust Wrap,
	// or we can test the wrapped version.
	// Since Wrap is in this package, let's test the return values directly for "Unit" feel.

	req := httptest.NewRequest("GET", "/api/experiments", nil)

	res, err := api.ListExperiments(req)
	if err != nil {
		t.Fatalf("Handler returned error: %v", err)
	}

	// Assert Type
	exps, ok := res.([]models.Experiment)
	if !ok {
		t.Fatalf("Expected []models.Experiment, got %T", res)
	}

	if len(exps) != 2 {
		t.Errorf("Expected 2 experiments, got %d", len(exps))
	}
}

func TestGetExperiment(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	id := createTestExperiment(t, api, "Target Exp")

	// Set PathValue for Go 1.22 routing if we were using ServeMux.
	// But calling handler directly means r.PathValue might be empty unless we set it.
	// The standard library's `Request.SetPathValue` (Go 1.22) allows this.

	req := httptest.NewRequest("GET", "/api/experiments/1", nil)
	req.SetPathValue("id", "1") // Assuming ID is 1 for first insert in fresh DB

	res, err := api.GetExperiment(req)
	if err != nil {
		t.Fatalf("Handler returned error: %v", err)
	}

	exp, ok := res.(*models.Experiment)
	if !ok {
		t.Fatalf("Expected *models.Experiment, got %T", res)
	}

	if exp.ID != id {
		t.Errorf("Expected ID %d, got %d", id, exp.ID)
	}
	if exp.Name != "Target Exp" {
		t.Errorf("Expected Name 'Target Exp', got '%s'", exp.Name)
	}
}

func TestControlExperiment(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	id := createTestExperiment(t, api, "Control Exp")

	req := httptest.NewRequest("POST", "/api/experiments/1/control", strings.NewReader(`{"command": "stop"}`))
	req.SetPathValue("id", "1")

	res, err := api.ControlExperiment(req)
	if err != nil {
		t.Fatalf("Handler returned error: %v", err)
	}

	respMap, ok := res.(map[string]string)
	if !ok {
		t.Fatalf("Expected map[string]string, got %T", res)
	}
	if respMap["status"] != "updated" {
		t.Errorf("Expected status updated, got %s", respMap["status"])
	}

	// Verify DB state
	exp, _ := api.DB.GetExperimentByID(id)
	if exp.ExecutionControl != "stop" {
		t.Errorf("Expected execution_control 'stop', got '%s'", exp.ExecutionControl)
	}
}
