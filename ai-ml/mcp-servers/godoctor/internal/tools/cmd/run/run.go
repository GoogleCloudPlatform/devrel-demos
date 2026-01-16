// Package run implements the safe.shell tool.
package run

import (
	"context"
	"fmt"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/danicat/godoctor/internal/roots"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const (
	// maxOutputSize is the limit for direct return (16KB).
	maxOutputSize = 16 * 1024
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["cmd.run"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters for the safe_shell tool.
type Params struct {
	Command string   `json:"command" jsonschema:"The command to execute (e.g. 'go', 'ls', 'grep')"`
	Args    []string `json:"args" jsonschema:"The arguments for the command"`
	Input   string   `json:"input,omitempty" jsonschema:"Optional data to send to the command's stdin"`
	Force   bool     `json:"force,omitempty" jsonschema:"If true, bypasses advisory nudges (use sparingly)"`
}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.Command == "" {
		return errorResult("command cannot be empty"), nil, nil
	}

	// 1. Validation
	if err := validateCommand(args.Command, args.Args, args.Force); err != nil {
		return errorResult(err.Error()), nil, nil
	}

	// 2. Execution with timeout
	ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, args.Command, args.Args...)

	// Setup Stdin if provided
	if args.Input != "" {
		cmd.Stdin = strings.NewReader(args.Input)
	}

	// Capture output
	output, err := cmd.CombinedOutput()

	// 3. Handle Result
	status := "Success"
	if err != nil {
		status = fmt.Sprintf("Error: %v", err)
	}

	resultText := string(output)
	if len(resultText) > maxOutputSize {
		// If output is too large, we could save it to a resource or truncate
		resultText = resultText[:maxOutputSize] + "\n\n[Output truncated due to size...]"
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{
				Text: fmt.Sprintf("Command: %s %s\nStatus: %s\n\nOutput:\n%s",
					args.Command, strings.Join(args.Args, " "), status, resultText),
			},
		},
	}, nil, nil
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}

// Security Configuration
var (
	// commandAllowList contains commands that are always allowed if arguments pass.
	commandAllowList = map[string]bool{
		"go":    true,
		"ls":    true,
		"grep":  true,
		"find":  true,
		"cat":   true,
		"head":  true,
		"tail":  true,
		"pwd":   true,
		"echo":  true,
		"date":  true,
		"env":   true,
		"which": true,
		"du":    true,
		"stat":  true,
		"git":   true, // git is mostly safe in a local repo for read ops
	}

	// safeRunBlockList contains commands that are strictly forbidden.
	safeRunBlockList = map[string]string{
		"rm":    "Deleting files is forbidden. Use specialized tools for file management if available.",
		"mv":    "Moving/Renaming should be done via specialized tools.",
		"cp":    "Copying should be done via specialized tools.",
		"sudo":  "Privilege escalation is strictly forbidden.",
		"chmod": "Changing permissions is forbidden.",
		"chown": "Changing ownership is forbidden.",
		"kill":  "Terminating processes is forbidden.",
		"ssh":   "Remote connections are forbidden.",
		"curl":  "Network requests are forbidden. Use documentation tools for external info.",
		"wget":  "Network requests are forbidden.",
		"sh":    "Shell spawning is forbidden. Run commands directly.",
		"bash":  "Shell spawning is forbidden.",
		"zsh":   "Shell spawning is forbidden.",
	}

	// fileOps marks commands that read files directly to ensure they stay in bounds.
	fileOps = map[string]bool{
		"cat":  true,
		"head": true,
		"tail": true,
		"grep": true,
		"stat": true,
	}

	// nudgeMap provides advisory warnings for commands that have specialized tool alternatives.
	nudgeMap = map[string]string{
		"go build":   "Use 'go.build' for project compilation.",
		"go test":    "Use 'go.test' for running tests.",
		"go mod":     "Use 'go.mod' for dependency management.",
		"go get":     "Use 'go.get' for adding packages.",
		"go install": "Use 'go.install' for installing binaries.",
		"go fmt":     "Files are auto-formatted during 'file.edit'.",
		"go doc":     "Use 'go.docs' to query documentation.",
		"go docs":    "Use 'go.docs' to query documentation.",
		"go vet":     "Use 'go.lint' for code analysis.",
		"go lint":    "Use 'go.lint' for code analysis.",
	}
	metaCharRegex = regexp.MustCompile(`[|><&;$` + "`" + `]`)
)

func validateCommand(cmd string, args []string, force bool) error {
	// 1. Metacharacter Check
	if metaCharRegex.MatchString(cmd) {
		return fmt.Errorf("command contains illegal shell metacharacters")
	}

	// 2. Blocklist
	if msg, blocked := safeRunBlockList[cmd]; blocked {
		return fmt.Errorf("command '%s' is blocked: %s", cmd, msg)
	}

	// 3. Nudge (Advisory)
	if !force {
		// specific check on the full command string for "go build" etc which are multi-word conceptually but passed as separate args
		if cmd == "go" && len(args) > 0 {
			fullCmd := "go " + args[0]
			if msg, exists := nudgeMap[fullCmd]; exists {
				return fmt.Errorf("advisory: %s (set force=true to override)", msg)
			}
		}
		if msg, exists := nudgeMap[cmd]; exists {
			return fmt.Errorf("advisory: %s (set force=true to override)", msg)
		}
	}

	// 5. Hardened Argument Validation (Universal)
	// We strictly enforce that the agent cannot reference paths outside the registered roots.
	for _, arg := range args {
		// Skip flags (e.g. "-v", "--output=file"), but check their values if attached
		if strings.HasPrefix(arg, "-") {
			// Weak heuristic: if a flag contains specific forbidden patterns, block it.
			// e.g. "--path=/etc" or "--path=../"
			if strings.Contains(arg, "/..") || strings.Contains(arg, "../") {
				return fmt.Errorf("argument '%s' contains unsafe path patterns", arg)
			}
			continue
		}

		// Block Path Traversal
		if strings.Contains(arg, "..") {
			return fmt.Errorf("argument '%s' contains path traversal '..'", arg)
		}

		// If it looks like a path (contains / or .go), validate it
		if strings.Contains(arg, "/") || strings.HasSuffix(arg, ".go") {
			if _, err := roots.Global.Validate(arg); err != nil {
				// We don't block EVERYTHING that isn't a path (e.g. "fmt")
				// but if it looks like a path and fails validation, we block it.
				// However, absolute paths that fail validation should definitely be blocked.
				if filepath.IsAbs(arg) {
					return err
				}
				// For relative paths that look like paths, we are more careful.
				// If it's a simple name like "main.go" and it's not in roots, Validate will catch it if it's outside.
			}
		}
	}

	// 6. Check File Ops (Explicitly allowed after validation)
	if fileOps[cmd] {
		// Already validated by the loop above regarding paths.
		return nil
	}

	// 7. Generic AllowList check
	if !commandAllowList[cmd] {
		return fmt.Errorf("command '%s' is not in the safe allowlist", cmd)
	}

	return nil
}
