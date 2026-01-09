package db

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestMessagesView(t *testing.T) {
	// Setup
	tmpDir, _ := os.MkdirTemp("", "tenkai-db-test")
	defer os.RemoveAll(tmpDir)
	dbPath := filepath.Join(tmpDir, "test.db")
	database, err := Open(dbPath)
	if err != nil {
		t.Fatalf("Failed to open DB: %v", err)
	}
	defer database.Close()

	// Insert Experiment & Run
	exp := &Experiment{Name: "Test", Timestamp: time.Now()}
	expID, err := database.CreateExperiment(exp)
	if err != nil {
		t.Fatalf("Failed to create experiment: %v", err)
	}

	run := &RunResult{ExperimentID: expID, Status: "RUNNING"}
	runID, err := database.SaveRunResult(run)
	if err != nil {
		t.Fatalf("Failed to save run: %v", err)
	}

	// Save Message Event (using struct with tags)
	type MessageEvent struct {
		Timestamp time.Time `json:"timestamp"`
		Role      string    `json:"role"`
		Content   string    `json:"content"`
		Delta     bool      `json:"delta"`
	}

	msg := MessageEvent{
		Timestamp: time.Now(),
		Role:      "user",
		Content:   "Hello World",
	}

	if err := database.SaveRunEvent(runID, "message", msg); err != nil {
		t.Fatalf("Failed to save event: %v", err)
	}

	// Query via View (GetMessages)
	msgs, err := database.GetMessages(runID)
	if err != nil {
		t.Fatalf("Failed to get messages: %v", err)
	}

	if len(msgs) != 1 {
		t.Fatalf("Expected 1 message, got %d", len(msgs))
	}
	if msgs[0].Role != "user" {
		t.Errorf("Expected role 'user', got '%s'", msgs[0].Role)
	}
	if msgs[0].Content != "Hello World" {
		t.Errorf("Expected content 'Hello World', got '%s'", msgs[0].Content)
	}
}

func TestGetMessages_Aggregation(t *testing.T) {
	// Setup
	tmpDir, _ := os.MkdirTemp("", "tenkai-db-test-agg")
	defer os.RemoveAll(tmpDir)
	dbPath := filepath.Join(tmpDir, "test.db")
	database, err := Open(dbPath)
	if err != nil {
		t.Fatalf("Failed to open DB: %v", err)
	}
	defer database.Close()

	// Insert Run
	exp := &Experiment{Name: "TestAgg", Timestamp: time.Now()}
	expID, _ := database.CreateExperiment(exp)
	run := &RunResult{ExperimentID: expID, Status: "RUNNING"}
	runID, _ := database.SaveRunResult(run)

	// Define Event Struct
	type MessageEvent struct {
		Role    string `json:"role"`
		Content string `json:"content"`
		Delta   bool   `json:"delta"`
	}

	// Sequence:
	// 1. User: "Tell me a story."
	// 2. Model: "Once" (Start)
	// 3. Model: " upon" (Delta)
	// 4. Model: " a time." (Delta)
	// 5. User: "Stop."

	events := []MessageEvent{
		{Role: "user", Content: "Tell me a story.", Delta: false},
		{Role: "model", Content: "Once", Delta: false},
		{Role: "model", Content: " upon", Delta: true},
		{Role: "model", Content: " a time.", Delta: true},
		{Role: "user", Content: "Stop.", Delta: false},
	}

	for _, e := range events {
		if err := database.SaveRunEvent(runID, "message", e); err != nil {
			t.Fatalf("Failed to save event: %v", err)
		}
		// Small sleep to ensure timestamp ordering if implementation relies on it (though ID should suffice)
		// time.Sleep(1 * time.Millisecond)
	}

	// Verify
	msgs, err := database.GetMessages(runID)
	if err != nil {
		t.Fatalf("Failed to get messages: %v", err)
	}

	if len(msgs) != 3 {
		t.Fatalf("Expected 3 aggregated messages, got %d", len(msgs))
	}

	// Check Model Message (Index 1)
	if msgs[1].Role != "model" {
		t.Errorf("Expected role model, got %s", msgs[1].Role)
	}
	expectedContent := "Once upon a time."
	if msgs[1].Content != expectedContent {
		t.Errorf("Aggregation failed. Expected '%s', got '%s'", expectedContent, msgs[1].Content)
	}

	// Check Final User Message
	if msgs[2].Content != "Stop." {
		t.Errorf("Last message mismatch. Got '%s'", msgs[2].Content)
	}
}
