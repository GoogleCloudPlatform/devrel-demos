package config

import (
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
