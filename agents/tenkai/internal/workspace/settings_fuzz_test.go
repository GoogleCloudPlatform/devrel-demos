package workspace

import (
	"encoding/json"
	"testing"

	"gopkg.in/yaml.v3"
)

// FuzzSettingsGeneration tests that ANY random YAML input can be sanitized
// and merged into a JSON-compatible structure without crashing or producing invalid JSON.
func FuzzSettingsGeneration(f *testing.F) {
	// 1. Seed Corpus with known problematic cases
	f.Add([]byte(`
name: test
content:
  general:
    previewFeatures: true
`))
	f.Add([]byte(`
nested:
  map:
    key: value
`))
	f.Add([]byte(`
list:
  - item1
  - sublist:
      key: val
`))

	f.Fuzz(func(t *testing.T, data []byte) {
		// 2. Unmarshal random bytes as YAML (simulating config loading)
		var input interface{}
		if err := yaml.Unmarshal(data, &input); err != nil {
			return // Invalid YAML is not our problem here
		}

		// 3. The input might be map[string]interface{}, map[interface{}]interface{}, slice, or scalar.
		// Our deepMerge expects map[string]interface{} as dest.
		// But sanitizeValue handles anything.

		// Let's simulate merging this into an existing settings map
		dst := make(map[string]interface{})

		// If input is a map, we try to merge it.
		// If input is map[interface{}]interface{} (which yaml.v3 produces), we must handle it.

		// Convert input to map if possible to simulate deepMerge call
		// But first, we test sanitizeValue directly on the raw input
		sanitized := sanitizeValue(input)

		// 4. Verification: Can we Marshal this to JSON?
		if _, err := json.Marshal(sanitized); err != nil {
			t.Fatalf("sanitizeValue produced JSON-incompatible output: %v\nInput type: %T\nValue: %#v", err, input, input)
		}

		// 5. Test deepMerge if input is a map
		if inputMap, ok := asMap(input); ok {
			// Create a complex existing state
			dst["existing"] = "value"
			dst["nested"] = map[string]interface{}{"foo": "bar"}

			// Merge!
			if err := deepMerge(dst, inputMap); err != nil {
				// deepMerge should generally not fail on type mismatches, it overwrites.
				// If it returns error, it's worth checking why.
				// Currently deepMerge returns error only if recursion fails?
				t.Logf("deepMerge returned error (acceptable?): %v", err)
			}

			// Verify Result is valid JSON
			if _, err := json.Marshal(dst); err != nil {
				t.Fatalf("deepMerge produced JSON-incompatible dest: %v", err)
			}
		}
	})
}

// TestSanitizeValue_CornerCases tests specific edge cases explicitly
func TestSanitizeValue_CornerCases(t *testing.T) {
	tests := []struct {
		name  string
		input interface{}
		want  interface{} // We mainly check type compatibility via JSON marshal
	}{
		{
			name: "MapInterfaceInterface",
			input: map[interface{}]interface{}{
				"key": "value",
				123:   "non-string-key", // Should be stringified
			},
		},
		{
			name: "NestedMapInterface",
			input: map[string]interface{}{
				"deep": map[interface{}]interface{}{
					"foo": "bar",
				},
			},
		},
		{
			name: "SliceOfMaps",
			input: []interface{}{
				map[interface{}]interface{}{"k": "v"},
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := sanitizeValue(tt.input)

			// Verify it marshals
			if _, err := json.Marshal(got); err != nil {
				t.Errorf("Sanitized value failed JSON marshal: %v", err)
			}

			// Verify structure if possible
			// For MapInterfaceInterface, we expect "123" key
			if tt.name == "MapInterfaceInterface" {
				m := got.(map[string]interface{})
				if m["123"] != "non-string-key" {
					t.Errorf("Expected '123' key, got %v", m)
				}
			}
		})
	}
}

// TestDeepMerge_Overwrites tests specific merge behaviors
func TestDeepMerge_Logic(t *testing.T) {
	dst := map[string]interface{}{
		"a": 1,
		"b": map[string]interface{}{
			"c": 2,
		},
	}
	src := map[string]interface{}{
		"b": map[string]interface{}{
			"d": 3, // Should merge
		},
		"e": 4, // Should add
	}

	if err := deepMerge(dst, src); err != nil {
		t.Fatalf("deepMerge failed: %v", err)
	}

	// Verify
	if dst["a"] != 1 {
		t.Error("key 'a' lost")
	}
	if dst["e"] != 4 {
		t.Error("key 'e' missing")
	}

	bMap := dst["b"].(map[string]interface{})
	if bMap["c"] != 2 {
		t.Error("nested key 'c' lost")
	}
	if bMap["d"] != 3 {
		t.Error("nested key 'd' missing")
	}
}

// Helpers for test to assert types
func isJSONCompatible(v interface{}) bool {
	_, err := json.Marshal(v)
	return err == nil
}
