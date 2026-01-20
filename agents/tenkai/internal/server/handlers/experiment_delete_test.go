package handlers

import (
	"fmt"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func TestDeleteExperiment(t *testing.T) {
	api, tmpDir := setupAPI(t)
	defer os.RemoveAll(tmpDir)

	cwd, _ := os.Getwd()
	runsDir := filepath.Join(cwd, "experiments", ".runs")
	defer os.RemoveAll(filepath.Join(cwd, "experiments")) // Cleanup

	createRunDir := func(exp *models.Experiment) string {
		expDirName := workspace.GetExperimentFolderName(exp.Timestamp, exp.Name)
		targetDir := filepath.Join(runsDir, expDirName)
		if err := os.MkdirAll(targetDir, 0755); err != nil {
			t.Fatalf("Failed to create test run dir: %v", err)
		}
		return targetDir
	}

	t.Run("Delete Unlocked Experiment", func(t *testing.T) {
		exp := &models.Experiment{
			Name:      "Unlocked Exp",
			Timestamp: time.Now(),
			Status:    "COMPLETED",
			IsLocked:  false,
		}
		id, _ := api.DB.CreateExperiment(exp)
		dir := createRunDir(exp)

		req := httptest.NewRequest("DELETE", fmt.Sprintf("/api/experiments/%d", id), nil)
		req.SetPathValue("id", fmt.Sprintf("%d", id))

		if _, err := api.DeleteExperiment(req); err != nil {
			t.Fatalf("Handler returned error: %v", err)
		}

		if _, err := api.DB.GetExperimentByID(id); err == nil {
			t.Error("Experiment should have been deleted")
		}
		if _, err := os.Stat(dir); !os.IsNotExist(err) {
			t.Error("Directory should have been deleted")
		}
	})

	t.Run("Delete Locked Experiment", func(t *testing.T) {
		exp := &models.Experiment{
			Name:      "Locked Exp",
			Timestamp: time.Now(),
			Status:    "COMPLETED",
			IsLocked:  true,
		}
		id, _ := api.DB.CreateExperiment(exp)
		dir := createRunDir(exp)

		req := httptest.NewRequest("DELETE", fmt.Sprintf("/api/experiments/%d", id), nil)
		req.SetPathValue("id", fmt.Sprintf("%d", id))

		if _, err := api.DeleteExperiment(req); err == nil {
			t.Fatal("Expected error when deleting locked experiment")
		}

		if _, err := api.DB.GetExperimentByID(id); err != nil {
			t.Error("Locked experiment should NOT have been deleted")
		}
		if _, err := os.Stat(dir); os.IsNotExist(err) {
			t.Error("Locked directory should NOT have been deleted")
		}
	})

	t.Run("Delete All Experiments (Safety Check)", func(t *testing.T) {
		// Create 1 unlocked, 1 locked
		unlocked := &models.Experiment{Name: "Bulk Unlocked", Timestamp: time.Now(), IsLocked: false}
		locked := &models.Experiment{Name: "Bulk Locked", Timestamp: time.Now().Add(1 * time.Hour), IsLocked: true}

		uid, _ := api.DB.CreateExperiment(unlocked)
		lid, _ := api.DB.CreateExperiment(locked)
		uDir := createRunDir(unlocked)
		lDir := createRunDir(locked)

		req := httptest.NewRequest("DELETE", "/api/experiments", nil)
		if _, err := api.DeleteAllExperiments(req); err != nil {
			t.Fatalf("DeleteAll returned error: %v", err)
		}

		// Verify Unlocked Gone
		if _, err := api.DB.GetExperimentByID(uid); err == nil {
			t.Error("Unlocked experiment should be gone")
		}
		if _, err := os.Stat(uDir); !os.IsNotExist(err) {
			t.Error("Unlocked directory should be gone")
		}

		// Verify Locked Remains
		if _, err := api.DB.GetExperimentByID(lid); err != nil {
			t.Error("Locked experiment should remain")
		}
		if _, err := os.Stat(lDir); os.IsNotExist(err) {
			t.Error("Locked directory should remain")
		}
	})
}
