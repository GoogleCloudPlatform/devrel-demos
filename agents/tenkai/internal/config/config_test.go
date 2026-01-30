package config

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"gopkg.in/yaml.v3"
)

func TestValidationRule_YamlRoundTrip(t *testing.T) {
	original := ValidationRule{
		Type:           "command",
		Command:        "./hello",
		Stdin:          "some input",
		StdinDelay:     "500ms",
		ExpectExitCode: intPtr(0),
	}

	data, err := yaml.Marshal(original)
	if err != nil {
		t.Fatalf("Marshal failed: %v", err)
	}
	t.Logf("Marshaled YAML:\n%s", string(data))

	var loaded ValidationRule
	if err := yaml.Unmarshal(data, &loaded); err != nil {
		t.Fatalf("Unmarshal failed: %v", err)
	}

	if loaded.StdinDelay != "500ms" {
		t.Errorf("Expected StdinDelay '500ms', got '%s'", loaded.StdinDelay)
	}
	if loaded.Stdin != "some input" {
		t.Errorf("Expected Stdin 'some input', got '%s'", loaded.Stdin)
	}
}

func intPtr(i int) *int {
	return &i
}

func TestLoad(t *testing.T) {
	// Create a temporary directory for config and related files
	tmpDir := t.TempDir()

	// Create dummy related files
	settingsPath := filepath.Join(tmpDir, "settings.json")
	os.WriteFile(settingsPath, []byte("{}"), 0644)

	configPath := filepath.Join(tmpDir, "config.yaml")
	configContent := fmt.Sprintf(`
name: test-config
alternatives:
  - name: alt1
    command: echo
    settings_path: settings.json
scenarios:
  - scen1
`)
	if err := os.WriteFile(configPath, []byte(configContent), 0644); err != nil {
		t.Fatal(err)
	}

	cfg, err := Load(configPath)
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}

	if cfg.Name != "test-config" {
		t.Errorf("Expected Name 'test-config', got '%s'", cfg.Name)
	}
	if len(cfg.Alternatives) != 1 {
		t.Errorf("Expected 1 alternative, got %d", len(cfg.Alternatives))
	}

	// Check path resolution
	expectedSettingsPath := settingsPath
	if cfg.Alternatives[0].SettingsPath != expectedSettingsPath {
		t.Errorf("Expected absolute settings path '%s', got '%s'", expectedSettingsPath, cfg.Alternatives[0].SettingsPath)
	}

	// Check defaults
	if cfg.Repetitions != 1 {
		t.Errorf("Expected default Repetitions 1, got %d", cfg.Repetitions)
	}
}

func TestLoadScenarioConfig(t *testing.T) {
	tmpDir := t.TempDir()
	scenPath := filepath.Join(tmpDir, "scenario.yaml")
	content := `
name: test-scenario
task: do something
`
	if err := os.WriteFile(scenPath, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}

	cfg, err := LoadScenarioConfig(scenPath)
	if err != nil {
		t.Fatalf("LoadScenarioConfig failed: %v", err)
	}

	if cfg.Name != "test-scenario" {
		t.Errorf("Expected Name 'test-scenario', got '%s'", cfg.Name)
	}
	if cfg.Task != "do something" {
		t.Errorf("Expected Task 'do something', got '%s'", cfg.Task)
	}
}

func TestParse(t *testing.T) {
	content := `
name: parsed-config
repetitions: 5
`
	cfg, err := Parse([]byte(content))
	if err != nil {
		t.Fatalf("Parse failed: %v", err)
	}

	if cfg.Name != "parsed-config" {
		t.Errorf("Expected Name 'parsed-config', got '%s'", cfg.Name)
	}
	if cfg.Repetitions != 5 {
		t.Errorf("Expected Repetitions 5, got %d", cfg.Repetitions)
	}
}
