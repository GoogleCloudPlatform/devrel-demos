// Package run implements the safe.shell tool.
package run

import (
	"context"
	"fmt"
	"io"
	"os"
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
	// defaultTimeout is the default execution timeout.
	defaultTimeout = 5 * time.Second
	// maxTimeout is the maximum allowed timeout.
	maxTimeout = 5 * time.Minute
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
	Command        string    `json:"command" jsonschema:"The command to execute (e.g. 'go', 'ls', './my_binary')"`
	Args           *[]string `json:"args,omitempty" jsonschema:"The arguments for the command"`
	Stdin          string    `json:"stdin,omitempty" jsonschema:"Optional data to send to the command's stdin"`
	OutputFile     string    `json:"output_file,omitempty" jsonschema:"Optional path to write stdout/stderr to (replaces shell redirection)"`
	Force          bool      `json:"force,omitempty" jsonschema:"If true, bypasses advisory nudges (use sparingly)"`
	TimeoutSeconds int       `json:"timeout_seconds,omitempty" jsonschema:"Timeout in seconds (default: 5, max: 300)"`
}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.Command == "" {
		return errorResult("command cannot be empty"), nil, nil
	}

	// Dereference args safely
	var cmdArgs []string
	if args.Args != nil {
		cmdArgs = *args.Args
	}

	// 1. Validation
	if err := validateCommand(args.Command, cmdArgs, args.Force); err != nil {
		return errorResult(err.Error()), nil, nil
	}

	// 2. Execution with timeout
	timeout := defaultTimeout
	if args.TimeoutSeconds > 0 {
		timeout = time.Duration(args.TimeoutSeconds) * time.Second
		if timeout > maxTimeout {
			timeout = maxTimeout
		}
	}
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, args.Command, cmdArgs...)

	// Capture output
	var stdout, stderr strings.Builder

	// If OutputFile is specified, we'll write to it AND buffer for the return value (up to a limit)
	// But to avoid OOM on huge files, we just use the strings.Builder for the return value
	// and a MultiWriter if a file is present.

	var outWriter io.Writer = &stdout
	var errWriter io.Writer = &stderr

	if args.OutputFile != "" {
		// Validate output path
		if _, err := roots.Global.Validate(args.OutputFile); err != nil {
			return errorResult(fmt.Sprintf("invalid output_file: %v", err)), nil, nil
		}

		f, err := os.Create(args.OutputFile)
		if err != nil {
			return errorResult(fmt.Sprintf("failed to create output file: %v", err)), nil, nil
		}
		defer f.Close()

		// Write combined output to file, but separate for streams
		// Note: mirroring standard shell redirection where > captures stdout.
		// We will capture both to the file for simplicity in this tool's context ("log capture")
		// or we could stick to stdout only. For developer tools, capturing both is usually desired.
		outWriter = io.MultiWriter(&stdout, f)
		errWriter = io.MultiWriter(&stderr, f)
	}

	cmd.Stdout = outWriter
	cmd.Stderr = errWriter

	// Setup Stdin pipe for interactive commands
	var stdinPipe io.WriteCloser
	if args.Stdin != "" {
		var err error
		stdinPipe, err = cmd.StdinPipe()
		if err != nil {
			return errorResult(fmt.Sprintf("failed to create stdin pipe: %v", err)), nil, nil
		}
	}

	// Start the command (non-blocking)
	start := time.Now()
	if err := cmd.Start(); err != nil {
		return errorResult(fmt.Sprintf("failed to start command: %v", err)), nil, nil
	}

	// Write input in a goroutine to avoid blocking
	if stdinPipe != nil {
		go func() {
			// Note: We do NOT close stdinPipe here (Keep-Alive strategy).
			// This allows interactive servers to stay alive until the context timeout.
			io.WriteString(stdinPipe, args.Stdin)
		}()
	}

	// Wait for command to complete
	err := cmd.Wait()
	duration := time.Since(start)

	// Combine output for merged view
	stdoutStr := stdout.String()
	stderrStr := stderr.String()
	output := stdoutStr
	if stderrStr != "" {
		if output != "" {
			output += "\n"
		}
		output += "--- STDERR ---\n" + stderrStr
	}

	// 3. Handle Result and Truncation
	status := "Success"
	hint := ""
	if err != nil {
		// Default to error status
		status = fmt.Sprintf("Error (%v)", err)

		// Check if it's just a non-zero exit code
		if exitErr, ok := err.(*exec.ExitError); ok {
			status = fmt.Sprintf("Failed (Exit Code %d)", exitErr.ExitCode())
			// User request: Treat exit codes as tool success, just command failure.
			// Agents should read the output to see the failure.
			err = nil
		}

		// Runtime Hints for Robustness
		// 1. EOF Trap (False Negative Prevention)
		if strings.Contains(output, "EOF") || strings.Contains(output, "file already closed") {
			hint = "\n\n[Runtime Hint] The process exited with error (EOF). CHECK THE OUTPUT ABOVE! If it contains valid JSON, you can ignore this error."
		}
		// 2. Protocol Mismatch Trap
		if strings.Contains(output, "invalid character 'C'") || strings.Contains(output, "Content-Length") {
			hint = "\n\n[Runtime Hint] Protocol Error detected. Do not send 'Content-Length' headers. Send raw newline-delimited JSON-RPC messages only."
		}
		// 3. Timeout Hint (Explicitly mention the 5s limit)
		if ctx.Err() == context.DeadlineExceeded {
			status = fmt.Sprintf("Timeout (Killed after %v) - Output Captured", timeout)
			hint += "\n\n[Runtime Hint] As expected, the process was killed by timeout to flush interactive output."
			err = nil // Suppress error for timeout
		}
	}

	if len(output) > maxOutputSize {
		// Sophisticated Truncation: Stream to temp file and return head/tail
		tempFile, tempErr := os.CreateTemp("", "godoctor-run-*.log")
		if tempErr == nil {
			defer tempFile.Close()
			tempFile.WriteString(output)

			head := output[:1024]
			tail := output[len(output)-1024:]
			output = fmt.Sprintf("WARNING: Output truncated (size: %d bytes). Full log written to %s\n\n[...HEAD...]\n%s\n\n... [TRUNCATED] ...\n\n[...TAIL...]\n%s",
				len(output), tempFile.Name(), head, tail)
		} else {
			// Fallback if temp file fails
			output = output[:maxOutputSize] + "\n\n[Output truncated due to size...]"
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{
				Text: fmt.Sprintf("Command: %s %s\nStatus: %s\nDuration: %v\nOutput File: %s\n\nOutput:\n%s%s",
					args.Command, strings.Join(cmdArgs, " "), status, duration, args.OutputFile, output, hint),
			},
		},
		IsError: err != nil,
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
		"go":      true,
		"python":  true,
		"python3": true,
		"node":    true,
		"npm":     true,
		"cargo":   true,
		"ls":      true,
		"grep":    true,
		"find":    true,
		"cat":     true,
		"head":    true,
		"tail":    true,
		"pwd":     true,
		"echo":    true,
		"date":    true,
		"env":     true,
		"which":   true,
		"du":      true,
		"stat":    true,
		"rm":      true, // Allowed but validated for paths
		"mv":      true, // Allowed but validated for paths
		"cp":      true, // Allowed but validated for paths
		"mkdir":   true, // Allowed but validated for paths
		"rmdir":   true, // Allowed but validated for paths
	}

	// safeRunBlockList contains commands that are strictly forbidden.
	safeRunBlockList = map[string]string{
		"git":   "Git commands should be performed via go.get or other semantic tools.",
		"sudo":  "Privilege escalation is strictly forbidden.",
		"chmod": "Changing permissions is forbidden.",
		"chown": "Changing ownership is forbidden.",
		"kill":  "Terminating processes is forbidden.",
		"ssh":   "Remote connections are forbidden.",
		"curl":  "Network requests are forbidden.",
		"wget":  "Network requests are forbidden.",

		"sh":   "Shell spawning is forbidden. Use 'output_file' parameter for redirection.",
		"bash": "Shell spawning is forbidden. Use 'output_file' parameter for redirection.",
		"zsh":  "Shell spawning is forbidden.",
	}

	// fileOps marks commands that read files directly to ensure they stay in bounds.
	fileOps = map[string]bool{
		"cat":   true,
		"head":  true,
		"tail":  true,
		"grep":  true,
		"stat":  true,
		"rm":    true,
		"mv":    true,
		"cp":    true,
		"mkdir": true,
		"rmdir": true,
	}

	// nudgeMap provides advisory warnings for commands that have specialized tool alternatives.
	nudgeMap = map[string]string{
		"grep":       "Do not use grep for code search. Use 'file.search' or 'symbol.inspect'.",
		"ls":         "Do not use shell to list files. Use 'file.list' or 'project.map'.",
		"go build":   "Use 'go.build' for project compilation.",
		"go test":    "Use 'go.test' for running tests.",
		"go mod":     "Use 'go.mod' for dependency management.",
		"go get":     "Use 'go.get' for adding packages.",
		"go install": "Use 'go.install' for installing binaries.",
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
		// Multi-word nudge check
		if cmd == "go" && len(args) > 0 {
			fullCmd := "go " + args[0]
			if msg, exists := nudgeMap[fullCmd]; exists {
				return fmt.Errorf("advisory: %s (set force=true to override)", msg)
			}
		}
		// Single word nudge check
		if msg, exists := nudgeMap[cmd]; exists {
			return fmt.Errorf("advisory: %s (set force=true to override)", msg)
		}
	}

	// 4. Hardened Argument Validation (Universal)
	for _, arg := range args {
		if strings.HasPrefix(arg, "-") {
			if strings.Contains(arg, "/..") || strings.Contains(arg, "../") {
				return fmt.Errorf("argument '%s' contains unsafe path patterns", arg)
			}
			continue
		}

		if strings.Contains(arg, "..") {
			return fmt.Errorf("argument '%s' contains path traversal '..'", arg)
		}

		// Detect Silent Redirection attempts
		if strings.ContainsAny(arg, ">|") {
			return fmt.Errorf("argument '%s' contains shell metacharacters (> or |). Redirection is not supported via args; use 'output_file' parameter", arg)
		}

		// Validate path containment
		if strings.Contains(arg, "/") || strings.HasSuffix(arg, ".go") {
			if _, err := roots.Global.Validate(arg); err != nil {
				if filepath.IsAbs(arg) {
					return err
				}
			}
		}
	}

	// 5. Allowlist and Local Binary
	if commandAllowList[cmd] {
		return nil
	}

	if strings.Contains(cmd, "/") {
		if !force && (filepath.IsAbs(cmd) || strings.Contains(cmd, "..")) {
			return fmt.Errorf("local binary path '%s' must be relative and within the project", cmd)
		}
		if _, err := roots.Global.Validate(cmd); err == nil {
			return nil
		}
	}

	return fmt.Errorf("command '%s' is not in the safe allowlist", cmd)
}
