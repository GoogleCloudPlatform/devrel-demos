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
	"strconv"
	"strings"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
)

type ValidationReport struct {
	OverallSuccess bool                `json:"overall_success"`
	TestsPassed    int                 `json:"tests_passed"`
	TestsFailed    int                 `json:"tests_failed"`
	LintIssues     int                 `json:"lint_issues"`
	Coverage       float64             `json:"coverage,omitempty"`
	Items          []ValidationItem    `json:"items"`
	DetailedTests  []models.TestResult `json:"-"` // Not serialized to validation_report JSON, saved to test_results table
	DetailedLints  []models.LintIssue  `json:"-"` // Not serialized to validation_report JSON, saved to lint_results table
}

type ValidationItem struct {
	Type        string  `json:"type"`
	Status      string  `json:"status"` // "PASS", "FAIL"
	Description string  `json:"description"`
	Details     string  `json:"details,omitempty"`
	Coverage    float64 `json:"coverage,omitempty"`
}

func (r *Runner) Validate(ctx context.Context,
	wsPath string, rules []config.ValidationRule, stdout string) (*ValidationReport, error) {
	report := &ValidationReport{
		OverallSuccess: true,
		Items:          make([]ValidationItem, 0),
		DetailedTests:  make([]models.TestResult, 0),
		DetailedLints:  make([]models.LintIssue, 0),
	}

	for _, rule := range rules {
		var item ValidationItem
		var err error
		var tPass, tFail, lIssues int
		var tests []models.TestResult
		var lints []models.LintIssue

		switch rule.Type {
		case "test":
			tests, item, tPass, tFail, err = r.validateTest(ctx, wsPath, rule)
			report.TestsPassed += tPass
			report.TestsFailed += tFail
			report.DetailedTests = append(report.DetailedTests, tests...)
			if item.Coverage > 0 {
				report.Coverage = item.Coverage
			}
		case "lint":
			lints, item, lIssues, err = r.validateLint(ctx, wsPath, rule)
			report.LintIssues += lIssues
			report.DetailedLints = append(report.DetailedLints, lints...)
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

		report.Items = append(report.Items, item)
	}

	return report, nil
}

// ApplyValidationReport applies the results of a validation report to a run result model.
func (r *Runner) ApplyValidationReport(run *models.RunResult, report *ValidationReport) {
	run.IsSuccess = report.OverallSuccess
	run.TestsPassed = report.TestsPassed
	run.TestsFailed = report.TestsFailed
	run.LintIssues = report.LintIssues

	jsonBytes, _ := json.Marshal(report)
	run.ValidationReport = string(jsonBytes)

	if run.IsSuccess {
		run.Reason = db.ReasonSuccess
	} else {
		run.Reason = db.ReasonFailedValidation
	}
}

func (r *Runner) validateTest(ctx context.Context, wsPath string, rule config.ValidationRule) ([]models.TestResult, ValidationItem, int, int, error) {
	target := rule.Target
	if target == "" {
		return nil, ValidationItem{
			Type:    "test",
			Status:  "FAIL",
			Details: "Error: No test target specified in validation rule (e.g., target: './...')",
		}, 0, 0, nil
	}

	cmd := exec.CommandContext(ctx, "go", "test", "-json", "-cover", target)
	cmd.Dir = wsPath // Run in workspace
	var out bytes.Buffer
	cmd.Stdout = &out
	// Ignore exit code error, we parse JSON
	_ = cmd.Run()

	scanner := bufio.NewScanner(strings.NewReader(out.String()))
	testsFound := false
	passedCount := 0
	failedCount := 0
	coverage := 0.0
	var detailsBuilder strings.Builder
	packageFailed := false

	var results []models.TestResult

	for scanner.Scan() {
		var entry struct {
			Action  string
			Package string
			Test    string
			Output  string
			Time    string
			Elapsed float64
		}
		if err := json.Unmarshal(scanner.Bytes(), &entry); err == nil {
			if entry.Action == "run" || entry.Action == "pass" || entry.Action == "fail" {
				testsFound = true
			}

			// Capture individual test results
			if entry.Test != "" && (entry.Action == "pass" || entry.Action == "fail" || entry.Action == "skip") {
				status := strings.ToUpper(entry.Action) // PASS, FAIL, SKIP
				results = append(results, models.TestResult{
					Name:       entry.Test,
					Status:     status,
					DurationNS: int64(entry.Elapsed * 1e9),
					Output:     entry.Output,
				})
			}

			if entry.Action == "pass" && entry.Test != "" {
				passedCount++
				detailsBuilder.WriteString(fmt.Sprintf("PASS: %s\n", entry.Test))
			}
			if entry.Action == "fail" {
				if entry.Test != "" {
					failedCount++
					detailsBuilder.WriteString(fmt.Sprintf("FAIL: %s\n", entry.Test))
				} else {
					packageFailed = true
				}
			}
			// Only capture coverage from output lines associated with the package result (Test == ""),
			// avoiding noise from individual test logs if they happen to contain the string.
			if entry.Action == "output" && entry.Test == "" && strings.Contains(entry.Output, "coverage:") {
				parts := strings.Split(entry.Output, " ")
				for i, p := range parts {
					if p == "coverage:" && i+1 < len(parts) {
						covStr := strings.TrimRight(parts[i+1], "%")
						if val, err := strconv.ParseFloat(covStr, 64); err == nil {
							coverage = val
						}
					}
				}
			}
		}
	}

	item := ValidationItem{
		Type:     "test",
		Coverage: coverage,
	}
	covDesc := ""
	if coverage > 0 {
		covDesc = fmt.Sprintf(" (Cov: %.1f%%)", coverage)
	}
	item.Description = fmt.Sprintf("Run tests on %s%s", target, covDesc)

	// Determine success
	item.Status = "PASS"
	if !testsFound {
		item.Status = "FAIL"
		item.Details = "No tests found or test execution failed entirely"
		return nil, item, 0, 0, nil
	}

	if failedCount > 0 {
		item.Status = "FAIL"
	}

	if rule.MinCoverage > 0 && coverage < rule.MinCoverage {
		item.Status = "FAIL"
	}

	// Build details message
	var msg strings.Builder
	msg.WriteString(fmt.Sprintf("%d passed, %d tests failed%s", passedCount, failedCount, covDesc))
	if rule.MinCoverage > 0 {
		msg.WriteString(fmt.Sprintf(" (Requirement: >= %.1f%%)", rule.MinCoverage))
	}
	msg.WriteString(":\n\n")

	if packageFailed && !testsFound {
		item.Status = "FAIL"
		msg.WriteString("ERROR: Package compilation or initialization failed (no tests were executed).\n")
	}

	msg.WriteString(detailsBuilder.String())
	item.Details = msg.String()

	return results, item, passedCount, failedCount, nil
}

func (r *Runner) validateLint(ctx context.Context, wsPath string, rule config.ValidationRule) ([]models.LintIssue, ValidationItem, int, error) {
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

	// Intermediate structs for golangci-lint JSON output
	type glPos struct {
		Filename string `json:"Filename"`
		Line     int    `json:"Line"`
		Column   int    `json:"Column"`
	}
	type glIssue struct {
		FromLinter string `json:"FromLinter"`
		Text       string `json:"Text"`
		Severity   string `json:"Severity"`
		Pos        glPos  `json:"Pos"`
	}
	var result struct {
		Issues []glIssue `json:"Issues"`
	}

	var issues []models.LintIssue

	if err := json.Unmarshal(out.Bytes(), &result); err == nil {
		// Convert to db.LintIssue
		for _, i := range result.Issues {
			issues = append(issues, models.LintIssue{
				File:     i.Pos.Filename,
				Line:     i.Pos.Line,
				Col:      i.Pos.Column,
				Message:  i.Text,
				Severity: i.Severity,
				RuleID:   i.FromLinter,
			})
		}
	}

	// Check exclusions
	var finalIssuesList []models.LintIssue
	finalIssuesCount := 0
	var detailsBuilder strings.Builder
	for _, issue := range issues {
		ignored := false
		for _, excl := range rule.Exclude {
			if strings.Contains(issue.Message, excl) || strings.Contains(issue.RuleID, excl) {
				ignored = true
				break
			}
		}
		if !ignored {
			finalIssuesCount++
			finalIssuesList = append(finalIssuesList, issue)
			// Format: file:line:col [rule] message
			detailsBuilder.WriteString(fmt.Sprintf("%s:%d:%d [%s] %s\n",
				issue.File, issue.Line, issue.Col, issue.RuleID, issue.Message))
		}
	}

	item := ValidationItem{
		Type:        "lint",
		Description: fmt.Sprintf("Lint check on %s (Max: %d)", target, rule.MaxIssues),
	}

	if finalIssuesCount <= rule.MaxIssues {
		item.Status = "PASS"
		if finalIssuesCount == 0 {
			item.Details = fmt.Sprintf("Found %d issues (allowed %d)", finalIssuesCount, rule.MaxIssues)
		} else {
			item.Details = fmt.Sprintf("Found %d issues (allowed %d):\n\n%s", finalIssuesCount, rule.MaxIssues, detailsBuilder.String())
		}
	} else {
		item.Status = "FAIL"
		item.Details = fmt.Sprintf("Found %d issues (allowed %d):\n\n%s", finalIssuesCount, rule.MaxIssues, detailsBuilder.String())
	}

	return finalIssuesList, item, finalIssuesCount, nil
}

func (r *Runner) validateCommand(ctx context.Context, wsPath string, rule config.ValidationRule) (ValidationItem, error) {
	// Wrap command in sh -c to support pipes and shell syntax
	fullCmd := rule.Command
	if len(rule.Args) > 0 {
		fullCmd += " " + strings.Join(rule.Args, " ")
	}
	cmd := exec.CommandContext(ctx, "/bin/sh", "-c", fullCmd)
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
