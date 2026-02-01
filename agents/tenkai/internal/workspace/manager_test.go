package workspace

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
)

func TestManager_PathResolution(t *testing.T) {
	// Create temporary directory structure
	tmpDir, err := os.MkdirTemp("", "tenkai-test-*")
	if err != nil {
		t.Fatalf("failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	// Structure:
	// /assets/scenarios/1/scenario.yaml
	// /assets/templates/default/config.yaml
	// /workspace (base path)

	assetsDir := filepath.Join(tmpDir, "assets")
	scenariosDir := filepath.Join(assetsDir, "scenarios")
	templatesDir := filepath.Join(assetsDir, "templates")
	runsDir := filepath.Join(assetsDir, "_runs")
	basePath := filepath.Join(tmpDir, "workspace")

	if err := os.MkdirAll(scenariosDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(templatesDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(runsDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(basePath, 0755); err != nil {
		t.Fatal(err)
	}

	// Create dummy scenario
	if err := os.MkdirAll(filepath.Join(scenariosDir, "scen1"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(scenariosDir, "scen1", "scenario.yaml"), []byte("name: scen1"), 0644); err != nil {
		t.Fatal(err)
	}

	// Create dummy template
	if err := os.MkdirAll(filepath.Join(templatesDir, "tmpl1"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(templatesDir, "tmpl1", "config.yaml"), []byte("name: tmpl1"), 0644); err != nil {
		t.Fatal(err)
	}

	// Initialize Manager with explicit paths
	m := New(basePath, templatesDir, runsDir, scenariosDir)

	// Test ListScenarios
	scens := m.ListScenarios()
	if len(scens) != 1 {
		t.Errorf("expected 1 scenario, got %d", len(scens))
	}
	if len(scens) > 0 && scens[0].ID != "scen1" {
		t.Errorf("expected scenario ID 'scen1', got %s", scens[0].ID)
	}

	// Test ListTemplates
	tmpls := m.ListTemplates()
	if len(tmpls) != 1 {
		t.Errorf("expected 1 template, got %d", len(tmpls))
	}
	if len(tmpls) > 0 && tmpls[0].ID != "tmpl1" {
		t.Errorf("expected template ID 'tmpl1', got %s", tmpls[0].ID)
	}

	// Test FindExperimentDir
	now := time.Now()
	expName := "test-exp"
	expFolderName := GetExperimentFolderName(now, expName)
	expPath := filepath.Join(runsDir, expFolderName)
	if err := os.MkdirAll(expPath, 0755); err != nil {
		t.Fatal(err)
	}

	foundDir, err := m.FindExperimentDir(now, expName)
	if err != nil {
		t.Fatalf("failed to find experiment dir: %v", err)
	}
	if foundDir != expPath {
		t.Errorf("expected %s, got %s", expPath, foundDir)
	}
}

func TestManager_DefaultTemplatePath(t *testing.T) {
	// Create temporary directory structure for default fallback
	tmpDir, err := os.MkdirTemp("", "tenkai-test-default-*")
	if err != nil {
		t.Fatalf("failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	// Structure:
	// /workspace/templates/default/config.yaml

	basePath := filepath.Join(tmpDir, "workspace")
	defaultTemplatesDir := filepath.Join(basePath, "templates")

	if err := os.MkdirAll(defaultTemplatesDir, 0755); err != nil {
		t.Fatal(err)
	}

	if err := os.MkdirAll(filepath.Join(defaultTemplatesDir, "tmpl_default"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(defaultTemplatesDir, "tmpl_default", "config.yaml"), []byte("name: default"), 0644); err != nil {
		t.Fatal(err)
	}

	// Initialize Manager without explicit templates dir
	m := New(basePath, "", "") // Empty experimentTemplatesDir and runsDir

	// Test ListTemplates (should fallback to basePath/experiments/templates)
	tmpls := m.ListTemplates()
	if len(tmpls) != 1 {
		t.Errorf("expected 1 template from default path, got %d", len(tmpls))
	}
}

func TestPrepare_SettingsGeneration(t *testing.T) {
	tmpDir := t.TempDir()
	// Need to provide scenarios dir
	scenariosDir := filepath.Join(tmpDir, "scenarios")
	os.MkdirAll(scenariosDir, 0755)

	mgr := New(tmpDir, tmpDir, tmpDir, scenariosDir)

	// Mock Scenario
	scenDir := filepath.Join(scenariosDir, "test-scen")
	os.MkdirAll(scenDir, 0755)
	os.WriteFile(filepath.Join(scenDir, "scenario.yaml"), []byte("name: test\ntask: hi"), 0644)

	// Mock Config with Mixed-Mode Settings Block
	opts := WorkspaceOptions{
		SettingsBlocks: []config.SettingsBlock{
			{
				Name: "Enable Preview",
				Content: map[string]interface{}{
					"general": map[string]interface{}{
						"previewFeatures": true,
					},
				},
			},
		},
	}

	info, err := mgr.Prepare(tmpDir, "alt1", "test-scen", 1, opts)
	if err != nil {
		t.Fatalf("Prepare failed: %v", err)
	}

	// Read settings.json
	settingsPath := filepath.Join(info.Project, ".gemini", "settings.json")
	content, err := os.ReadFile(settingsPath)
	if err != nil {
		t.Fatalf("Failed to read settings.json: %v", err)
	}

	t.Logf("Generated settings.json: %s", string(content))

	if !strings.Contains(string(content), `"previewFeatures": true`) {
		t.Error("settings.json missing 'previewFeatures': true")
	}
	if !strings.Contains(string(content), `"general": {`) {
		t.Error("settings.json missing 'general' block")
	}
}
