package collector

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestCollectCodeLines(t *testing.T) {
	// Create a temporary directory for our test files
	tmpDir, err := os.MkdirTemp("", "test-collect-code-lines-")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	// Create dummy Go files
	file1Content := "package main\n\nfunc main() {}"
	file1Path := filepath.Join(tmpDir, "main.go")
	if err := os.WriteFile(file1Path, []byte(file1Content), 0644); err != nil {
		t.Fatalf("Failed to write file1: %v", err)
	}

	subDir := filepath.Join(tmpDir, "sub")
	if err := os.Mkdir(subDir, 0755); err != nil {
		t.Fatalf("Failed to create subdir: %v", err)
	}
	file2Content := "package sub\n\nfunc helper() {}"
	file2Path := filepath.Join(subDir, "helper.go")
	if err := os.WriteFile(file2Path, []byte(file2Content), 0644); err != nil {
		t.Fatalf("Failed to write file2: %v", err)
	}

	// Call the function we are testing
	codeLines, err := collectCodeLines([]string{tmpDir})
	if err != nil {
		t.Fatalf("collectCodeLines failed: %v", err)
	}

	// Define the expected result
	expected := []CodeLine{
		{Package: tmpDir, File: "main.go", LineNumber: 1, Content: "package main"},
		{Package: tmpDir, File: "main.go", LineNumber: 2, Content: ""},
		{Package: tmpDir, File: "main.go", LineNumber: 3, Content: "func main() {}"},
		{Package: subDir, File: "helper.go", LineNumber: 1, Content: "package sub"},
		{Package: subDir, File: "helper.go", LineNumber: 2, Content: ""},
		{Package: subDir, File: "helper.go", LineNumber: 3, Content: "func helper() {}"},
	}

	// Check if the result matches the expectation
	if !reflect.DeepEqual(codeLines, expected) {
		t.Errorf("collectCodeLines() got = %v, want %v", codeLines, expected)
	}
}