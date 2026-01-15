package workspace

import (
	"os"
	"path/filepath"
	"testing"
)

func setupTestManager(t *testing.T) (*Manager, string) {
	tmpDir := t.TempDir()

	// Create templates/scenarios dir
	scenariosDir := filepath.Join(tmpDir, "scenarios")
	os.MkdirAll(scenariosDir, 0755)

	// Create templates/experiments/templates dir (internal structure expected by manager)
	// Manager expects BasePath, then looks into experiments/templates
	// And takes templatesDirs slice for scenarios.

	m := New(tmpDir, scenariosDir)
	return m, tmpDir
}

func TestScenarioCRUD(t *testing.T) {
	m, _ := setupTestManager(t)

	// Create
	id, err := m.CreateScenario("Test Scen", "Desc", "Task", nil, nil, nil)
	if err != nil {
		t.Fatalf("CreateScenario failed: %v", err)
	}

	// List
	scens := m.ListScenarios()
	if len(scens) != 1 {
		t.Errorf("Expected 1 scenario, got %d", len(scens))
	}
	if scens[0].ID != id {
		t.Errorf("Expected scenario ID %s, got %s", id, scens[0].ID)
	}

	// Get
	s, err := m.GetScenario(id)
	if err != nil {
		t.Fatalf("GetScenario failed: %v", err)
	}
	if s.Name != "Test Scen" {
		t.Errorf("Expected Name 'Test Scen', got %s", s.Name)
	}

	// Update
	err = m.UpdateScenario(id, "Updated Name", "Updated Desc", "Updated Task", nil, nil, nil)
	if err != nil {
		t.Fatalf("UpdateScenario failed: %v", err)
	}

	s2, _ := m.GetScenario(id)
	if s2.Name != "Updated Name" {
		t.Errorf("Expected Updated Name, got %s", s2.Name)
	}

	// Delete
	err = m.DeleteScenario(id)
	if err != nil {
		t.Fatalf("DeleteScenario failed: %v", err)
	}

	scens = m.ListScenarios()
	if len(scens) != 0 {
		t.Errorf("Expected 0 scenarios, got %d", len(scens))
	}
}

func TestTemplateCRUD(t *testing.T) {
	m, _ := setupTestManager(t)

	// Create
	id, err := m.CreateTemplate("Test Tmpl", "Desc", "name: test", nil)
	if err != nil {
		t.Fatalf("CreateTemplate failed: %v", err)
	}

	// List
	tmpls := m.ListTemplates()
	if len(tmpls) != 1 {
		t.Errorf("Expected 1 template, got %d", len(tmpls))
	}

	// Get
	tmpl, err := m.GetTemplate(id)
	if err != nil {
		t.Fatalf("GetTemplate failed: %v", err)
	}
	if tmpl.Name != "test" { // Comes from parsed yaml
		t.Errorf("Expected Name 'test' from yaml, got %s", tmpl.Name)
	}

	// Delete
	m.DeleteTemplate(id)
	if len(m.ListTemplates()) != 0 {
		t.Error("DeleteTemplate failed")
	}
}

func TestPrepareWorkspace(t *testing.T) {
	m, tmpDir := setupTestManager(t)

	// Create a dummy scenario to use
	sID, _ := m.CreateScenario("Scen1", "D", "Goal", nil, nil, nil)

	// Prepare
	opts := WorkspaceOptions{
		Context: "Context Content",
	}

	// experiments/exp/alt/scen/rep-1
	expDir := filepath.Join(tmpDir, "experiments", "exp1")

	info, err := m.PrepareWorkspace(expDir, "default", sID, 1, opts)
	if err != nil {
		t.Fatalf("PrepareWorkspace failed: %v", err)
	}

	// Verify dirs
	if _, err := os.Stat(info.Project); os.IsNotExist(err) {
		t.Error("Project dir not created")
	}
	if _, err := os.Stat(info.Home); os.IsNotExist(err) {
		t.Error("Home dir not created")
	}

	// Verify PROMPT.md (from task)
	prompt, _ := os.ReadFile(filepath.Join(info.Project, "PROMPT.md"))
	if string(prompt) != "Goal" {
		t.Errorf("PROMPT.md mismatch. Got %s", string(prompt))
	}

	// Verify GEMINI.md (from context)
	ctx, _ := os.ReadFile(filepath.Join(info.Project, "GEMINI.md"))
	if string(ctx) != "Context Content" {
		t.Errorf("GEMINI.md mismatch. Got %s", string(ctx))
	}
}
