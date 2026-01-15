package runner

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
)

func (r *Runner) validateCustom(ctx context.Context, wsPath string, rule config.ValidationRule, baseEnv map[string]string) (ValidationItem, error) {
	// Custom validator runs a script or binary located in the scenario assets (copied to workspace)
	// OR compiled from source.
	// For now, we assume the 'Path' refers to a file that is ALREADY in the workspace (copied via assets).
	// If it needs compilation (e.g. validator.go), we handle it here.

	validatorPath := filepath.Join(wsPath, rule.Path)
	if _, err := os.Stat(validatorPath); os.IsNotExist(err) {
		// Try to find it in the project root if not in workspace root?
		// Actually, assets are copied to wsPath directly.
		return ValidationItem{
			Type:        "custom",
			Status:      "FAIL",
			Description: fmt.Sprintf("Custom validator %s", rule.Path),
			Details:     fmt.Sprintf("Validator file not found at %s", validatorPath),
		}, nil
	}

	cmdName := validatorPath
	var cmdArgs []string

	// Detect type by extension
	ext := filepath.Ext(validatorPath)
	if ext == ".go" {
		// Compile it on the fly
		// go build -o validator rule.Path
		binPath := filepath.Join(wsPath, "validator.bin")
		buildCmd := exec.CommandContext(ctx, "go", "build", "-o", binPath, rule.Path)
		buildCmd.Dir = wsPath
		buildCmd.Env = r.prepareEnv(rule.Env, baseEnv)
		if out, err := buildCmd.CombinedOutput(); err != nil {
			return ValidationItem{
				Type:        "custom",
				Status:      "FAIL",
				Description: fmt.Sprintf("Custom validator %s (Build)", rule.Path),
				Details:     fmt.Sprintf("Failed to compile validator:\n%s", string(out)),
			}, nil
		}
		cmdName = binPath
	} else if ext == ".sh" {
		// Ensure executable
		os.Chmod(validatorPath, 0755)
	}

	// Prepare execution arguments
	// Inject template variables into Args
	for _, arg := range rule.Args {
		// Simple replacement for now
		val := strings.ReplaceAll(arg, "{{.WorkspacePath}}", wsPath)
		cmdArgs = append(cmdArgs, val)
	}

	cmd := exec.CommandContext(ctx, cmdName, cmdArgs...)
	cmd.Dir = wsPath
	cmd.Env = r.prepareEnv(rule.Env, baseEnv)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	exitCode := 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			return ValidationItem{
				Type:        "custom",
				Status:      "FAIL",
				Description: fmt.Sprintf("Custom validator %s", rule.Path),
				Details:     fmt.Sprintf("System Error executing validator: %v", err),
			}, nil
		}
	}

	item := ValidationItem{
		Type:        "custom",
		Description: fmt.Sprintf("Custom validator: %s", rule.Path),
	}

	if exitCode == 0 {
		item.Status = "PASS"
		item.Details = stdout.String()
	} else {
		item.Status = "FAIL"
		item.Details = fmt.Sprintf("Exit Code: %d\n\nSTDOUT:\n%s\n\nSTDERR:\n%s", exitCode, stdout.String(), stderr.String())
	}

	return item, nil
}
