package server

import (
	"bytes"
	"encoding/json"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strconv"
	"testing"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

// setupTestServer creates a new Server with a temporary database and workspace.
func setupTestServer(t *testing.T) (*Server, string) {
	// Create temp dir
	tmpDir, err := os.MkdirTemp("", "tenkai-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}

	// Initialize DB
	dbPath := filepath.Join(tmpDir, "test.db")
	database, err := db.Open(dbPath)
	if err != nil {
		t.Fatalf("Failed to open DB: %v", err)
	}

	// Initialize Workspace Manager
	scenariosDir := filepath.Join(tmpDir, "scenarios")
	os.MkdirAll(scenariosDir, 0755)
	wsMgr := workspace.New(tmpDir, scenariosDir)

	// Initialize Runner (mock or real with 0 concurrency to prevent spawning)
	r := runner.New(wsMgr, 0)
	r.SetDB(database)

	srv := New(database, r, wsMgr)
	return srv, tmpDir
}

func TestHealth(t *testing.T) {
	srv, tmpDir := setupTestServer(t)
	defer os.RemoveAll(tmpDir)

	req := httptest.NewRequest("GET", "/api/health", nil)
	w := httptest.NewRecorder()

	srv.router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "ok" {
		t.Errorf("Expected status 'ok', got %v", resp["status"])
	}
}

func TestExperimentsCRUD(t *testing.T) {
	srv, tmpDir := setupTestServer(t)
	defer os.RemoveAll(tmpDir)

	// 1. List Experiments (Empty)
	req := httptest.NewRequest("GET", "/api/experiments", nil)
	w := httptest.NewRecorder()
	srv.router.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("List experiments failed: %d", w.Code)
	}
	var exps []db.Experiment
	json.Unmarshal(w.Body.Bytes(), &exps)
	if len(exps) != 0 {
		t.Errorf("Expected 0 experiments, got %d", len(exps))
	}

	// 2. Create Experiment (Indirectly via StartExperimentRequest, but here we can mock DB insertion directly for test speed)
	// Or call the API endpoint if we want to test the handler logic.
	// The start endpoint spawns a process, which is hard to test.
	// Let's test GET by inserting into DB manually.

	exp := &db.Experiment{
		Name:      "Test Exp",
		Timestamp: time.Now(),
		Status:    "running",
	}
	id, err := srv.db.CreateExperiment(exp)
	if err != nil {
		t.Fatalf("Failed to insert experiment: %v", err)
	}

	// 3. Get Experiment by ID
	// Note: stdlib mux uses PathValue, but httptest request context might need setup for path vars?
	// The s.router is a http.ServeMux (Go 1.22+). It matches paths.
	// We need to construct the request URL correctly matching the pattern.
	req = httptest.NewRequest("GET", "/api/experiments/"+fmt_id(id), nil)
	w = httptest.NewRecorder()
	srv.router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Get experiment failed: %d", w.Code)
	}
	var fetchedExp db.Experiment
	json.Unmarshal(w.Body.Bytes(), &fetchedExp)
	if fetchedExp.Name != "Test Exp" {
		t.Errorf("Expected name 'Test Exp', got %s", fetchedExp.Name)
	}
}

func TestScenariosCRUD(t *testing.T) {
	srv, tmpDir := setupTestServer(t)
	defer os.RemoveAll(tmpDir)

	// 1. Create Scenario via Multipart Form
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	writer.WriteField("name", "Test Scenario")
	writer.WriteField("description", "A test description")
	writer.WriteField("prompt", "Do something")
	writer.WriteField("asset_type", "none")
	writer.Close()

	req := httptest.NewRequest("POST", "/api/scenarios", body)
	req.Header.Set("Content-Type", writer.FormDataContentType())
	w := httptest.NewRecorder()
	srv.router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Create scenario failed: %d - %s", w.Code, w.Body.String())
	}

	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	id := resp["id"]
	if id == "" {
		t.Fatal("Returned ID is empty")
	}

	// 2. Get Scenario
	req = httptest.NewRequest("GET", "/api/scenarios/"+id, nil)
	w = httptest.NewRecorder()
	srv.router.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("Get scenario failed: %d", w.Code)
	}
	var scen workspace.Scenario
	json.Unmarshal(w.Body.Bytes(), &scen)
	if scen.Name != "Test Scenario" {
		t.Errorf("Expected name 'Test Scenario', got %s", scen.Name)
	}

	// 3. Update Scenario (JSON)
	updatePayload := map[string]interface{}{
		"name":        "Updated Scenario",
		"description": "Updated desc",
		"task":        "Updated task",
	}
	jsonBody, _ := json.Marshal(updatePayload)
	req = httptest.NewRequest("PUT", "/api/scenarios/"+id, bytes.NewBuffer(jsonBody))
	w = httptest.NewRecorder()
	srv.router.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("Update scenario failed: %d", w.Code)
	}

	// Verify Update
	req = httptest.NewRequest("GET", "/api/scenarios/"+id, nil)
	w = httptest.NewRecorder()
	srv.router.ServeHTTP(w, req)
	json.Unmarshal(w.Body.Bytes(), &scen)
	if scen.Name != "Updated Scenario" {
		t.Errorf("Expected updated name, got %s", scen.Name)
	}
}

func TestTemplatesCRUD(t *testing.T) {
	srv, tmpDir := setupTestServer(t)
	defer os.RemoveAll(tmpDir)

	// 1. Create Template
	payload := map[string]interface{}{
		"name":         "Test Template",
		"description":  "Desc",
		"yaml_content": "name: Test Template\n",
		"files":        map[string]string{"SYSTEM.md": "You are a bot"},
	}
	jsonBody, _ := json.Marshal(payload)
	req := httptest.NewRequest("POST", "/api/templates", bytes.NewBuffer(jsonBody))
	w := httptest.NewRecorder()
	srv.router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Create template failed: %d", w.Code)
	}
	var resp map[string]string
	json.Unmarshal(w.Body.Bytes(), &resp)
	id := resp["id"]

	// 2. Get Template Config
	req = httptest.NewRequest("GET", "/api/templates/"+id+"/config", nil)
	w = httptest.NewRecorder()
	srv.router.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("Get template config failed: %d", w.Code)
	}

	// 3. Update Template
	updatePayload := map[string]interface{}{
		"yaml_content": "name: Updated Template\n",
		"files":        map[string]string{"GEMINI.md": "Context"},
	}
	jsonBody, _ = json.Marshal(updatePayload)
	req = httptest.NewRequest("PUT", "/api/templates/"+id+"/config", bytes.NewBuffer(jsonBody))
	w = httptest.NewRecorder()
	srv.router.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Errorf("Update template failed: %d", w.Code)
	}
}

// Helpers
func fmt_id(id int64) string {
	return strconv.Itoa(int(id))
}

func TestGetRunMessages_Integration(t *testing.T) {
	// 1. Setup
	srv, tmpDir := setupTestServer(t)
	defer os.RemoveAll(tmpDir)

	// 2. Seed Data
	exp := &db.Experiment{Name: "IntegrationTest", Timestamp: time.Now()}
	expID, _ := srv.db.CreateExperiment(exp)
	run := &db.RunResult{ExperimentID: expID, Status: "COMPLETED"}
	runID, _ := srv.db.SaveRunResult(run)

	// Insert Delta Events
	type MessageEvent struct {
		Role    string `json:"role"`
		Content string `json:"content"`
		Delta   bool   `json:"delta"`
	}
	events := []MessageEvent{
		{Role: "user", Content: "Hello", Delta: false},
		{Role: "model", Content: "Hi", Delta: false},
		{Role: "model", Content: " there", Delta: true},
	}
	for _, e := range events {
		srv.db.SaveRunEvent(runID, "message", e)
	}

	// Insert a generic event (e.g. result)
	srv.db.SaveRunEvent(runID, "result", map[string]interface{}{
		"status": "success",
		"stats":  map[string]int{"total_tokens": 100},
	})

	// 3. Happy Path: Get Messages
	req := httptest.NewRequest("GET", "/api/runs/"+fmt_id(runID)+"/messages", nil)
	w := httptest.NewRecorder()
	srv.router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected 200 OK, got %d", w.Code)
	}

	var messages []db.Message
	if err := json.NewDecoder(w.Body).Decode(&messages); err != nil {
		t.Fatalf("Failed to decode JSON: %v", err)
	}

	if len(messages) != 3 {
		t.Fatalf("Expected 3 aggregated messages (2 msg + 1 result), got %d", len(messages))
	}
	if messages[0].Content != "Hello" {
		t.Errorf("Msg 0 mismatch: %s", messages[0].Content)
	}
	if messages[1].Content != "Hi there" {
		t.Errorf("Msg 1 mismatch (aggregation failed): %s", messages[1].Content)
	}
	if messages[2].Role != "result" {
		t.Errorf("Msg 2 role mismatch. Expected 'result', got '%s'", messages[2].Role)
	}

	// 4. Sad Path: Run Not Found
	reqNotFound := httptest.NewRequest("GET", "/api/runs/99999/messages", nil)
	wNotFound := httptest.NewRecorder()
	srv.router.ServeHTTP(w, reqNotFound)

	// Note: GetMessages currently returns empty list for non-existent run, not 404.
	// This behavior is acceptable for list endpoints usually.
	if wNotFound.Code != http.StatusOK {
		t.Errorf("Expected 200 OK for empty list, got %d", wNotFound.Code)
	}
	var emptyMsgs []db.Message
	json.NewDecoder(wNotFound.Body).Decode(&emptyMsgs)
	if len(emptyMsgs) != 0 {
		t.Error("Expected empty list for non-existent run")
	}
	// 5. Sad Path: Invalid ID
	reqInvalid := httptest.NewRequest("GET", "/api/runs/abc/messages", nil)
	wInvalid := httptest.NewRecorder()
	srv.router.ServeHTTP(wInvalid, reqInvalid)

	if wInvalid.Code != http.StatusBadRequest {
		t.Errorf("Expected 400 Bad Request for invalid ID, got %d", wInvalid.Code)
	}
}

func TestGetRunMessages_EdgeCases(t *testing.T) {
	srv, tmpDir := setupTestServer(t)
	defer os.RemoveAll(tmpDir)
	expID, _ := srv.db.CreateExperiment(&db.Experiment{Name: "Edge", Timestamp: time.Now()})
	runID, _ := srv.db.SaveRunResult(&db.RunResult{ExperimentID: expID})

	// Case 1: Orphaned Delta (Delta true without prior message)
	// Should act as new message
	srv.db.SaveRunEvent(runID, "message", map[string]interface{}{
		"role": "model", "content": "I am orphan", "delta": true,
	})

	// Case 2: Switch Role without delta=false (Should start new message)
	srv.db.SaveRunEvent(runID, "message", map[string]interface{}{
		"role": "user", "content": "Interrupt", "delta": true,
	})

	msgs, _ := srv.db.GetMessages(runID, -1, 0)
	if len(msgs) != 2 {
		t.Fatalf("Expected 2 messages from edge case events, got %d", len(msgs))
	}
	if msgs[0].Content != "I am orphan" {
		t.Errorf("Orphan delta failed: %s", msgs[0].Content)
	}
	if msgs[1].Content != "Interrupt" {
		t.Errorf("Role switch failed: %s", msgs[1].Content)
	}
}
