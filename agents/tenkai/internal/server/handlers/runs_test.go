package handlers

import (
	"net/http/httptest"
	"os"
	"testing"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
)

func TestGetExperimentRuns(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	expID := createTestExperiment(t, api, "Run Test Exp")

	// Seed Runs
	run := &models.RunResult{ExperimentID: expID, Status: "COMPLETED", Duration: 100, Repetition: 1}
	api.DB.SaveRunResult(run)
	run2 := &models.RunResult{ExperimentID: expID, Status: "RUNNING", Repetition: 2}
	api.DB.SaveRunResult(run2)

	req := httptest.NewRequest("GET", "/api/experiments/1/runs", nil)
	req.SetPathValue("id", "1")

	res, err := api.GetExperimentRuns(req)
	if err != nil {
		t.Fatalf("Handler returned error: %v", err)
	}

	runs, ok := res.([]models.RunResult)
	if !ok {
		t.Fatalf("Expected []models.RunResult, got %T", res)
	}

	if len(runs) != 2 {
		t.Errorf("Expected 2 runs, got %d", len(runs))
	}
}

func TestGetRunFiles(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	expID := createTestExperiment(t, api, "File Test Exp")
	runID, _ := api.DB.SaveRunResult(&models.RunResult{ExperimentID: expID})

	// Save File
	file := &models.RunFile{
		RunID:       runID,
		Path:        "main.go",
		Content:     "package main",
		IsGenerated: true,
	}
	api.DB.SaveRunFile(file)

	req := httptest.NewRequest("GET", "/api/runs/1/files", nil)
	req.SetPathValue("id", "1")

	res, err := api.GetRunFiles(req)
	if err != nil {
		t.Fatalf("Handler returned error: %v", err)
	}

	files, ok := res.([]*models.RunFile)
	if !ok {
		t.Fatalf("Expected []*models.RunFile, got %T", res)
	}
	if len(files) != 1 {
		t.Errorf("Expected 1 file, got %d", len(files))
	}
	if files[0].Path != "main.go" {
		t.Errorf("Expected path main.go, got %s", files[0].Path)
	}
}

func TestGetRunMessages(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	expID := createTestExperiment(t, api, "Msg Test Exp")
	runID, _ := api.DB.SaveRunResult(&models.RunResult{ExperimentID: expID})

	// Save Message
	// Note: We need to use SaveRunEvent for messages if using the view-based architecture,
	// or internal/db logic handles it. The handler calls DB.GetMessages.
	// DB.GetMessages queries the 'run_events' table via View logic or directly?
	// It parses 'run_events'. So we should seed run_events.

	api.DB.SaveRunEvent(runID, "message", map[string]interface{}{
		"role":    "user",
		"content": "Hello",
	})

	req := httptest.NewRequest("GET", "/api/runs/1/messages", nil)
	req.SetPathValue("id", "1")

	res, err := api.GetRunMessages(req)
	if err != nil {
		t.Fatalf("Handler returned error: %v", err)
	}

	msgs, ok := res.([]models.Message)
	if !ok {
		// It might be []models.Message or *[]models.Message depending on impl?
		// Handler calls DB.GetMessages which returns []models.Message
		t.Fatalf("Expected []models.Message, got %T", res)
	}
	if len(msgs) != 1 {
		t.Errorf("Expected 1 message, got %d", len(msgs))
	}
	if msgs[0].Content != "Hello" {
		t.Errorf("Expected content 'Hello', got %s", msgs[0].Content)
	}
}
