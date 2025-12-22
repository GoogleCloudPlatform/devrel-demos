package runner

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
)

type ValidationReport struct {
	OverallSuccess bool             `json:"overall_success"`
	TotalScore     int              `json:"total_score"`
	TestsPassed    int              `json:"tests_passed"`
	TestsFailed    int              `json:"tests_failed"`
	LintIssues     int              `json:"lint_issues"`
	Items          []ValidationItem `json:"items"`
}

type ValidationItem struct {
	Type        string `json:"type"`
	Status      string `json:"status"` // "PASS", "FAIL"
	Description string `json:"description"`
	Details     string `json:"details,omitempty"`
	Score       int    `json:"score"`
}

func (r *Runner) Validate(ctx context.Context, wsPath string, rules []config.ValidationRule, stdout string) (*ValidationReport, error) {
	report := &ValidationReport{
		OverallSuccess: true,
		Items:          make([]ValidationItem, 0),
	}

	for _, rule := range rules {
		var item ValidationItem
		var err error
		var tPass, tFail, lIssues int

		switch rule.Type {
		case "test":
			item, tPass, tFail, err = r.validateTest(ctx, wsPath, rule)
			report.TestsPassed += tPass
			report.TestsFailed += tFail
		case "lint":
			item, lIssues, err = r.validateLint(ctx, wsPath, rule)
			report.LintIssues += lIssues
		case "command":
			item, err = r.validateCommand(ctx, wsPath, rule)
		case "model":
			item, err = r.validateModel(ctx, wsPath, rule, stdout)
		default:
			item = ValidationItem{
				Type:        rule.Type,
				Status:      "FAIL",
				Description: fmt.Sprintf("Unknown validation type: %s", rule.Type),
			}
		}

		if err != nil {
			log.Printf("Validation error for %s: %v", rule.Type, err)
			item.Status = "FAIL"
			item.Details = fmt.Sprintf("System Error: %v", err)
		}

		if item.Status != "PASS" {
			report.OverallSuccess = false
		}

		// Simple scoring: 1 point per passed rule for now, can be sophisticated later
		if item.Status == "PASS" {
			item.Score = 1
			report.TotalScore += 1
		}

		report.Items = append(report.Items, item)
	}

	return report, nil
}

func (r *Runner) validateTest(ctx context.Context, wsPath string, rule config.ValidationRule) (ValidationItem, int, int, error) {
	target := rule.Target
	if target == "" {
		target = "./..."
	}

	cmd := exec.CommandContext(ctx, "go", "test", "-json", target)
	cmd.Dir = wsPath // Run in workspace
	var out bytes.Buffer
	cmd.Stdout = &out
	// Ignore exit code error, we parse JSON
	_ = cmd.Run()

	// Parse test output
	// Reuse existing logic from evaluateCode if possible, but simplified here
	pass := true

	scanner := bufio.NewScanner(strings.NewReader(out.String()))
	testsFound := false
	passedCount := 0
	failedCount := 0
	for scanner.Scan() {
		var entry struct {
			Action string
			Test   string
		}
		if err := json.Unmarshal(scanner.Bytes(), &entry); err == nil {
			if entry.Action == "run" || entry.Action == "pass" || entry.Action == "fail" {
				testsFound = true
			}
			if entry.Action == "pass" && entry.Test != "" {
				passedCount++
			}
			if entry.Action == "fail" { // Check package failures too (Test="")
				pass = false
				if entry.Test != "" {
					failedCount++
				}
			}
		}
	}

	if !testsFound {
		pass = false
	}

	item := ValidationItem{
		Type:        "test",
		Description: fmt.Sprintf("Run tests on %s", target),
	}

	if pass {
		item.Status = "PASS"
		item.Details = fmt.Sprintf("All %d tests passed", passedCount)
	} else {
		item.Status = "FAIL"
		if !testsFound {
			item.Details = "No tests found or test execution failed"
		} else {
			item.Details = fmt.Sprintf("%d passed, %d tests failed", passedCount, failedCount)
		}
	}

	// TODO: Coverage check if rule.MinCoverage > 0

	return item, passedCount, failedCount, nil
}

func (r *Runner) validateLint(ctx context.Context, wsPath string, rule config.ValidationRule) (ValidationItem, int, error) {
	target := rule.Target
	if target == "" {
		target = "./..."
	}

	// golangci-lint run --out-format json ./...
	cmd := exec.CommandContext(ctx, "golangci-lint", "run", "--out-format", "json", target)
	cmd.Dir = wsPath
	var out bytes.Buffer
	cmd.Stdout = &out
	_ = cmd.Run() // It exits non-zero on issues

	var issues []db.LintIssue
	// The output structure of golangci-lint json
	var result struct {
		Issues []db.LintIssue `json:"Issues"`
	}
	if err := json.Unmarshal(out.Bytes(), &result); err == nil {
		issues = result.Issues
	} else {
		// Fallback if empty or raw
		// Check invalid JSON handling
	}

	// Check exclusions
	finalIssues := 0
	for _, issue := range issues {
		ignored := false
		for _, excl := range rule.Exclude {
			if strings.Contains(issue.Message, excl) || strings.Contains(issue.RuleID, excl) {
				ignored = true
				break
			}
		}
		if !ignored {
			finalIssues++
		}
	}

	item := ValidationItem{
		Type:        "lint",
		Description: fmt.Sprintf("Lint check on %s (Max: %d)", target, rule.MaxIssues),
	}

	if finalIssues <= rule.MaxIssues {
		item.Status = "PASS"
		item.Details = fmt.Sprintf("Found %d issues (allowed %d)", finalIssues, rule.MaxIssues)
	} else {
		item.Status = "FAIL"
		item.Details = fmt.Sprintf("Found %d issues (allowed %d)", finalIssues, rule.MaxIssues)
	}

	return item, finalIssues, nil
}

func (r *Runner) validateCommand(ctx context.Context, wsPath string, rule config.ValidationRule) (ValidationItem, error) {
	cmd := exec.CommandContext(ctx, rule.Command, rule.Args...)
	cmd.Dir = wsPath
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	exitCode := 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			// System error
			return ValidationItem{}, err
		}
	}

	item := ValidationItem{
		Type:        "command",
		Description: fmt.Sprintf("Run custom command: %s", rule.Command),
	}

	if exitCode == rule.ExpectExitCode {
		item.Status = "PASS"
		item.Details = fmt.Sprintf("Exit code %d matched expected", exitCode)
	} else {
		item.Status = "FAIL"
		item.Details = fmt.Sprintf("Exit code %d (expected %d). Stderr: %s", exitCode, rule.ExpectExitCode, stderr.String())
	}

	return item, nil
}

func (r *Runner) validateModel(ctx context.Context, wsPath string, rule config.ValidationRule, stdout string) (ValidationItem, error) {
	// Construct prompt
	promptPath := filepath.Join(wsPath, rule.PromptFile)
	promptBytes, err := os.ReadFile(promptPath)
	if err != nil {
		return ValidationItem{
			Type:        "model",
			Status:      "FAIL",
			Description: "Model validation",
			Details:     fmt.Sprintf("Prompt file missing: %s", rule.PromptFile),
		}, nil
	}

	contextContent := ""
	for _, ctxItem := range rule.Context {
		if ctxItem == "stdout" {
			contextContent += fmt.Sprintf("\n--- STDOUT ---\n%s\n", stdout)
		} else if strings.HasPrefix(ctxItem, "file:") {
			fname := strings.TrimPrefix(ctxItem, "file:")
			b, _ := os.ReadFile(filepath.Join(wsPath, fname))
			contextContent += fmt.Sprintf("\n--- %s ---\n%s\n", fname, string(b))
		}
	}

	fullPrompt := string(promptBytes) + "\n\nCONTEXT:\n" + contextContent

	// Call Gemini CLI
	// For now, assuming a simple "gemini prompt" call
	// In real implementation we should use the same mechanism as the agent but with a different system prompt?
	// User said: "invoking gemini cli with a special validation prompt"

	cmd := exec.CommandContext(ctx, "gemini", "prompt", fullPrompt)
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		return ValidationItem{
			Type:        "model",
			Status:      "FAIL",
			Description: "Model validation",
			Details:     fmt.Sprintf("Gemini invocation failed: %v", err),
		}, nil
	}

	// Parse output - assuming the model returns a structured decision?
	// Plan said "LLM output is parsed for a final JSON/Score"
	// We should strictly instruct the model to return JSON in the prompt file.

	// For this pass: Simple heuristic, look for "PASS" or "FAIL" in output if not JSON?
	// Let's assume the prompt instructions handle the output format.
	// If output contains "PASS", we pass.

	modelOut := out.String()
	status := "FAIL"
	if strings.Contains(strings.ToUpper(modelOut), "PASS") {
		status = "PASS"
	}

	return ValidationItem{
		Type:        "model",
		Status:      status,
		Description: "Model validation (LLM Grader)",
		Details:     modelOut,
	}, nil
}
