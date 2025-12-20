package collector

import (
	"os"
	"path/filepath"
	"testing"
)

func TestGetFunctionName(t *testing.T) {
	// Create a temporary directory and a dummy Go source file
	tmpDir, err := os.MkdirTemp("", "test-get-function-name-")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	sourceFile := filepath.Join(tmpDir, "main.go")
	sourceCode := `package main

func main() {
	// A comment
}

func anotherFunction() {
	// Another comment
}
`
	if err := os.WriteFile(sourceFile, []byte(sourceCode), 0644); err != nil {
		t.Fatalf("Failed to write source file: %v", err)
	}

	// Test cases
	testCases := []struct {
		name         string
		lineNumber   int
		expectedFunc string
		expectError  bool
	}{
		{"Inside main", 4, "main", false},
		{"Inside anotherFunction", 8, "anotherFunction", false},
		{"Outside any function", 1, "", true},
		{"On a blank line", 2, "", true},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			funcName, err := getFunctionName(sourceFile, tc.lineNumber)
			if (err != nil) != tc.expectError {
				t.Errorf("getFunctionName() error = %v, expectError %v", err, tc.expectError)
				return
			}
			if funcName != tc.expectedFunc {
				t.Errorf("getFunctionName() = %v, want %v", funcName, tc.expectedFunc)
			}
		})
	}
}
