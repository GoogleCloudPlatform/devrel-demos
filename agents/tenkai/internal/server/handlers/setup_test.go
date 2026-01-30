package handlers

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

// setupAPI creates a new API instance with temporary database and workspace.
func setupAPI(t *testing.T) (*API, string) {
	// Create temp dir
	tmpDir, err := os.MkdirTemp("", "tenkai-handler-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}

	// Initialize DB
	dbPath := filepath.Join(tmpDir, "test.db")
	database, err := db.Open("sqlite", dbPath)
	if err != nil {
		t.Fatalf("Failed to open DB: %v", err)
	}

	// Initialize Workspace Manager
	scenariosDir := filepath.Join(tmpDir, "scenarios")
	os.MkdirAll(scenariosDir, 0755)
	wsMgr := workspace.New(tmpDir, scenariosDir, scenariosDir)

	// Initialize Runner
	r := runner.New(wsMgr, 0)
	r.SetDB(database)

	api := New(database, r, wsMgr)
	return api, tmpDir
}

// createTestExperiment helper
func createTestExperiment(t *testing.T, api *API, name string) int64 {
	exp := &models.Experiment{
		Name: name,
		// other fields...
	}
	id, err := api.DB.CreateExperiment(exp)
	if err != nil {
		t.Fatalf("Failed to create experiment: %v", err)
	}
	return id
}
