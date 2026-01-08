package edit_code

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestEditCode(t *testing.T) {
	tmpDir := t.TempDir()
	filePath := filepath.Join(tmpDir, "test.go")

	// Helper to write file
	writeFile := func(content string) {
		if err := os.WriteFile(filePath, []byte(content), 0644); err != nil {
			t.Fatal(err)
		}
	}

	// Helper to read file
	readFile := func() string {
		b, err := os.ReadFile(filePath)
		if err != nil {
			t.Fatal(err)
		}
		return string(b)
	}

	ctx := context.Background()

	t.Run("Overwrite File (Valid)", func(t *testing.T) {
		params := EditCodeParams{
			FilePath:   filePath,
			NewContent: "package main\n\nfunc main() {}",
			Strategy:   "overwrite_file",
		}
		_, _, err := editCodeHandler(ctx, nil, params)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}

		got := readFile()
		if !strings.Contains(got, "package main") {
			t.Errorf("expected file to contain 'package main', got %q", got)
		}
	})

	t.Run("Single Match (Exact)", func(t *testing.T) {
		writeFile("package main\n\nfunc old() {}\n")
		params := EditCodeParams{
			FilePath:      filePath,
			SearchContext: "func old() {}",
			NewContent:    "func new() {}",
			Strategy:      "replace_block",
		}
		_, _, err := editCodeHandler(ctx, nil, params)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		got := readFile()
		if !strings.Contains(got, "func new() {}") {
			t.Errorf("replace failed, got %q", got)
		}
	})

	t.Run("Single Match (Fuzzy Whitespace)", func(t *testing.T) {
		writeFile("package main\n\nfunc old() {\n\tprintln(\"hi\")\n}\n")
		// Search context has different indentation (spaces instead of tabs)
		params := EditCodeParams{
			FilePath:      filePath,
			SearchContext: "func old() {\n  println(\"hi\")\n}",
			NewContent:    "func new() {}",
			Strategy:      "replace_block",
			Threshold:     0.8, // Allow some fuzziness
		}
		result, _, err := editCodeHandler(ctx, nil, params)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if result.IsError {
			content := ""
			if len(result.Content) > 0 {
				content = result.Content[0].(*mcp.TextContent).Text
			}
			t.Fatalf("tool returned error: %s", content)
		}
		got := readFile()
		if !strings.Contains(got, "func new() {}") {
			t.Errorf("fuzzy replace failed, got %q", got)
		}
	})

	t.Run("Syntax Error Rejection", func(t *testing.T) {
		writeFile("package main\n\nfunc main() {}\n")
		params := EditCodeParams{
			FilePath:   filePath,
			NewContent: "package main\n\nfunc main() { (((( }", // Syntax error
			Strategy:   "overwrite_file",
		}
		result, _, _ := editCodeHandler(ctx, nil, params)
		if !result.IsError {
			t.Fatal("expected error result for syntax error")
		}
		// Content should NOT have changed
		got := readFile()
		if strings.Contains(got, "((((") {
			t.Error("file was modified despite syntax error")
		}
	})

	t.Run("Replace All", func(t *testing.T) {
		writeFile("package main\nimport \"fmt\"\nfunc main() {\n\tfmt.Println(\"foo\")\n\tfmt.Println(\"foo\")\n}\n")
		params := EditCodeParams{
			FilePath:      filePath,
			SearchContext: "fmt.Println(\"foo\")",
			NewContent:    "fmt.Println(\"bar\")",
			Strategy:      "replace_all",
		}
		result, _, err := editCodeHandler(ctx, nil, params)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if result.IsError {
			t.Fatalf("tool returned error: %s", result.Content[0].(*mcp.TextContent).Text)
		}
		got := readFile()
		if strings.Count(got, "fmt.Println(\"bar\")") != 2 {
			t.Errorf("replace_all failed, expected 2 occurrences, got content:\n%q", got)
		}
	})

	t.Run("Feedback Best Match", func(t *testing.T) {
		writeFile("package main\n\nfunc correct() {\n\tprintln(\"hello\")\n}\n")
		// Major typo/garbage in search context
		params := EditCodeParams{
			FilePath:      filePath,
			SearchContext: "func correct() {\n  xxxxxx(\"hello\")\n}",
			NewContent:    "func new() {}",
			Strategy:      "replace_block",
		}
		result, _, err := editCodeHandler(ctx, nil, params)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if !result.IsError {
			t.Fatal("expected error for mismatch")
		}
		text := result.Content[0].(*mcp.TextContent).Text
		if !strings.Contains(text, "Best candidate found at line 3") {
			t.Errorf("expected best match feedback, got: %s", text)
		}
		if !strings.Contains(text, "Diff:") {
			t.Errorf("expected diff in feedback, got: %s", text)
		}
	})

	t.Run("Soft Validation Warning", func(t *testing.T) {
		// Valid syntax but invalid build (undefined function)
		dir := t.TempDir()

		// Initialize go.mod
		if err := os.WriteFile(filepath.Join(dir, "go.mod"), []byte("module example.com/test\ngo 1.21\n"), 0644); err != nil {
			t.Fatal(err)
		}

		file := filepath.Join(dir, "main.go")
		if err := os.WriteFile(file, []byte("package main\n\nfunc main() {}\n"), 0644); err != nil {
			t.Fatal(err)
		}

		params := EditCodeParams{
			FilePath:   file,
			NewContent: "package main\n\nfunc main() { undefinedFunc() }", // Syntax valid, Build invalid
			Strategy:   "overwrite_file",
		}

		result, _, err := editCodeHandler(ctx, nil, params)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}

		text := result.Content[0].(*mcp.TextContent).Text
		if !strings.Contains(text, "Success: File updated") {
			t.Errorf("expected success, got: %s", text)
		}
		if !strings.Contains(text, "Warning:** Analysis found issues") {
			t.Errorf("expected build warning, got: %s", text)
		}
		if !strings.Contains(text, "undefined: undefinedFunc") {
			// Output might vary slightly by go version, checking key part
			t.Errorf("expected specific build error in warning, got: %s", text)
		}
	})

	t.Run("AutoFix Typo", func(t *testing.T) {
		writeFile("package main\n\nfunc correct() {\n\tprintln(\"hello\")\n}\n")
		// Typo: prntln (missing i). Length 7 vs 6. Distance 1.
		// Score = 1 - 1/7 = 0.857. Wait, maxLen is 7 ("correct").
		// If context "prntln". maxLen 6. Score 1 - 1/6 = 0.833.
		// Default threshold 0.85. So it should FAIL by default.

		params := EditCodeParams{
			FilePath:      filePath,
			SearchContext: "func correct() {\n  prntln(\"hello\")\n}",
			NewContent:    "func new() {}",
			Strategy:      "replace_block",
			AutoFix:       true, // Should enable the fix
		}

		// We need to ensure the score < 0.85 so it triggers AutoFix logic.
		// "prntln" vs "println".
		// Context block len ~35.
		// 1 char difference in 35 chars is Score ~0.97.
		// So it would pass threshold 0.85 anyway!

		// To force AutoFix logic, we need a SHORT string where 1 char is significant penalty.
		// e.g. "func a()" vs "func b()".

		writeFile("func a() {}")
		params.SearchContext = "func b() {}" // Dist 1. Len 11. Score 1 - 1/11 = 0.90.
		// Still passes 0.85.

		// We need to raise threshold or make string shorter.
		// "a" vs "b". Dist 1. Len 1. Score 0.

		writeFile("package main\nvar a = 1\n")
		params.SearchContext = "var b = 1" // Dist 1.
		params.NewContent = "var c = 1"
		params.Threshold = 0.95 // Strict threshold

		// Without AutoFix, 0.9 < 0.95 -> Fail.
		// With AutoFix, Dist 1 -> Pass.

		_, _, err := editCodeHandler(ctx, nil, params)
		if err != nil {
			t.Fatalf("unexpected error with AutoFix: %v", err)
		}

		got := readFile()
		if !strings.Contains(got, "var c = 1") {
			t.Errorf("AutoFix failed to apply edit, got: %q", got)
		}
	})

	t.Run("Append Mode", func(t *testing.T) {
		writeFile("package main\n\nfunc main() {}\n")
		params := EditCodeParams{
			FilePath:   filePath,
			NewContent: "func helper() {}",
			Strategy:   "append",
		}
		_, _, err := editCodeHandler(ctx, nil, params)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}

		got := readFile()
		// goimports ensures one newline at end of file.
		// "package main\n\nfunc main() {}\nfunc helper() {}\n"
		if !strings.Contains(got, "func helper() {}") {
			t.Errorf("append failed, got %q", got)
		}
		if !strings.HasSuffix(strings.TrimSpace(got), "func helper() {}") {
			t.Errorf("content not appended at the end, got %q", got)
		}
	})
}
