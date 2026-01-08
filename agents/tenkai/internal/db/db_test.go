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
