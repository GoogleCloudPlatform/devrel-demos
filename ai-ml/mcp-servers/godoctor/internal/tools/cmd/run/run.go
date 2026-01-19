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
	"strconv"
	"strings"
	"sync"
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

// Process Management
var (
	activeProcesses = make(map[int]*exec.Cmd)
	processMu       sync.Mutex
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["safe_shell"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters for the safe_shell tool.
type Params struct {
	Command        string   `json:"command" jsonschema:"The command to execute (e.g. 'go', 'ls', './my_binary')"`
	Args           []string `json:"args,omitempty" jsonschema:"The arguments for the command"`
	Stdin          string   `json:"stdin,omitempty" jsonschema:"Optional data to send to the command's stdin"`
	CloseStdin     bool     `json:"close_stdin,omitempty" jsonschema:"If true, closes stdin after writing (Batch mode). Default false (Keep-Alive for REPLs)."`
	OutputFile     string   `json:"output_file,omitempty" jsonschema:"Optional path to write stdout/stderr to (replaces shell redirection)"`
	TimeoutSeconds int      `json:"timeout_seconds,omitempty" jsonschema:"Timeout in seconds (default: 5, max: 300)"`
	Background     bool     `json:"background,omitempty" jsonschema:"If true, run command in background and return PID (output_file required)"`
}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.Command == "" {
		return errorResult("command cannot be empty"), nil, nil
	}

	// 1. Validation
	advice, err := validateCommand(args.Command, args.Args)
	if err != nil {
		return &mcp.CallToolResult{
			IsError: true, // Fix: Silent Block Bug
			Content: []mcp.Content{
				&mcp.TextContent{Text: err.Error()},
			},
		}, nil, nil
	}

	// Background Check
	if args.Background && args.OutputFile == "" {
		return errorResult("background execution requires 'output_file' to capture logs"), nil, nil
	}

	// 2. Execution with timeout
	timeout := defaultTimeout
	if args.TimeoutSeconds > 0 {
		timeout = time.Duration(args.TimeoutSeconds) * time.Second
		if timeout > maxTimeout {
			timeout = maxTimeout
		}
	}

	// If background, we decouple context from the request context
	var cmdCtx context.Context
	var cancel context.CancelFunc

	if args.Background {
		cmdCtx = context.Background() // Command lives on its own
		// No timeout for background processes by default? Or should we still enforce one?
		// For now, let's assume background processes run until killed or they exit.
	} else {
		cmdCtx, cancel = context.WithTimeout(ctx, timeout)
		defer cancel()
	}

	cmd := exec.CommandContext(cmdCtx, args.Command, args.Args...)

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
		// Close file when command finishes?
		// For sync, yes. For async, we need to let the process write to it.
		// os.Create returns *os.File which implements WriteCloser.
		// If we defer close, we close it immediately for async.

		if args.Background {
			// For background, we just write to file, not memory buffer (too risky to buffer unbounded output)
			cmd.Stdout = f
			cmd.Stderr = f
		} else {
			defer f.Close()
			outWriter = io.MultiWriter(&stdout, f)
			errWriter = io.MultiWriter(&stderr, f)
			cmd.Stdout = outWriter
			cmd.Stderr = errWriter
		}
	} else {
		cmd.Stdout = outWriter
		cmd.Stderr = errWriter
	}

	// Setup Stdin pipe for interactive commands
	var stdinPipe io.WriteCloser
	if args.Stdin != "" {
		var err error
		stdinPipe, err = cmd.StdinPipe()
		if err != nil {
			return errorResult(fmt.Sprintf("failed to create stdin pipe: %v", err)), nil, nil
		}
	}

	// Start the command
	start := time.Now()
	if err := cmd.Start(); err != nil {
		return errorResult(fmt.Sprintf("failed to start command: %v", err)), nil, nil
	}

	// Write input in a goroutine to avoid blocking
	if stdinPipe != nil {
		go func() {
			io.WriteString(stdinPipe, args.Stdin)
			if args.CloseStdin {
				stdinPipe.Close()
			}
		}()
	}

	// --- BACKGROUND EXECUTION BRANCH ---
	if args.Background {
		pid := cmd.Process.Pid
		processMu.Lock()
		activeProcesses[pid] = cmd
		processMu.Unlock()

		// Cleanup goroutine
		go func() {
			cmd.Wait() // Wait for it to finish naturally
			processMu.Lock()
			delete(activeProcesses, pid)
			processMu.Unlock()
		}()

		return &mcp.CallToolResult{
			Content: []mcp.Content{
				&mcp.TextContent{
					Text: fmt.Sprintf("Background process started.\nPID: %d\nCommand: %s %s\nLogs: %s",
						pid, args.Command, strings.Join(args.Args, " "), args.OutputFile),
				},
			},
		}, nil, nil
	}
	// -----------------------------------

	// Wait for command to complete
	err = cmd.Wait()
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
		if cmdCtx.Err() == context.DeadlineExceeded {
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

	finalText := fmt.Sprintf("Command: %s %s\nStatus: %s\nDuration: %v\nOutput File: %s\n\nOutput:\n%s%s",
		args.Command, strings.Join(args.Args, " "), status, duration, args.OutputFile, output, hint)

	if advice != "" {
		finalText = fmt.Sprintf("[ADVICE]: %s\n---\n%s", advice, finalText)
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{
				Text: finalText,
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
	metaCharRegex = regexp.MustCompile(`[|><&;$` + "`" + `]`)
)

// Security Configuration
var (
	hardBlockList = map[string]string{
		// Danger
		"sudo":  "Privilege escalation is strictly forbidden.",
		"chown": "Changing ownership is forbidden.",
		"chmod": "Changing permissions is forbidden.",
		"ssh":   "Remote connections are forbidden.",
		"wget":  "Network requests are forbidden. Use dedicated tools if available.",
		"sh":    "Shell spawning is forbidden. Use 'output_file' parameter for redirection.",
		"bash":  "Shell spawning is forbidden. Use 'output_file' parameter for redirection.",
		"zsh":   "Shell spawning is forbidden.",

		// Process Safety
		"vim":  "Interactive editors are forbidden.",
		"nano": "Interactive editors are forbidden.",
		"top":  "Interactive tools are forbidden.",

		// Complexity
		"git": "Git commands should be handled by the user outside the agent.",
	}

	advisoryList = map[string]string{
		"ls":   "if you want to investigate the codebase, you might prefer 'file_list' or 'project_map'.",
		"cat":  "'file_read' is a more appropriate tool for reading files.",
		"head": "'file_read' is a more appropriate tool for reading files.",
		"tail": "'file_read' is a more appropriate tool for reading files.",
		"grep": "use 'symbol_inspect' for Go code search. For text search in non-Go files, grep is permitted.",
		"find": "use 'file_list' for structured directory mapping.",
	}

	integrityBarrierTriggers = map[string]bool{
		"sed": true,
		"awk": true,
	}
)

func validateCommand(cmd string, args []string) (string, error) {
	// 1. Metacharacter Check
	if metaCharRegex.MatchString(cmd) {
		return "", fmt.Errorf("command contains illegal shell metacharacters")
	}

	// 2. Hard Block List
	if msg, blocked := hardBlockList[cmd]; blocked {
		return "", fmt.Errorf("❌ Blocked: %s", msg)
	}

	// 3. Specialized Curl Validation
	if cmd == "curl" {
		for _, arg := range args {
			if arg == "-o" || strings.HasPrefix(arg, "--output") || arg == "-O" {
				return "", fmt.Errorf("❌ Blocked: curl is restricted to API interaction only. Writing to files via -o/-O/--output is forbidden")
			}
		}
	}

	// 4. Safe Kill Validation
	if cmd == "kill" {
		if len(args) == 0 {
			return "", fmt.Errorf("kill requires a PID argument")
		}
		var pid int
		found := false
		for _, arg := range args {
			if p, err := strconv.Atoi(arg); err == nil {
				pid = p
				found = true
				break
			}
		}
		if !found {
			return "", fmt.Errorf("could not parse PID from kill arguments")
		}
		processMu.Lock()
		_, exists := activeProcesses[pid]
		processMu.Unlock()
		if !exists {
			return "", fmt.Errorf("❌ Permission Denied: you can only kill processes started by this agent (PID %d not found)", pid)
		}
	}

	// 5. Code Integrity Barrier
	if integrityBarrierTriggers[cmd] {
		for _, arg := range args {
			if strings.HasSuffix(arg, ".go") {
				return "", fmt.Errorf("🛡️ Blocked: Modifying Go source files (*.go) via shell is forbidden to ensure integrity (goimports, syntax check). Use 'file_edit' or 'file_create' instead")
			}
		}
	}

	// 6. Hardened Argument Validation (Traversal & Redirection)
	for _, arg := range args {
		if strings.Contains(arg, "..") {
			return "", fmt.Errorf("argument '%s' contains path traversal '..'", arg)
		}
		if strings.ContainsAny(arg, ">|") {
			return "", fmt.Errorf("argument '%s' contains shell metacharacters (> or |). Redirection is not supported via args; use 'output_file' parameter", arg)
		}
		// Validate path containment
		if strings.Contains(arg, "/") {
			if _, err := roots.Global.Validate(arg); err != nil {
				if filepath.IsAbs(arg) {
					return "", err
				}
			}
		}
	}

	// 7. Path-based Command Validation (Security Restoration)
	if strings.Contains(cmd, "/") {
		if filepath.IsAbs(cmd) || strings.Contains(cmd, "..") {
			return "", fmt.Errorf("❌ Blocked: local binary path '%s' must be relative and within the project", cmd)
		}
		if _, err := roots.Global.Validate(cmd); err != nil {
			return "", fmt.Errorf("❌ Blocked: command '%s' is outside project roots: %v", cmd, err)
		}
	}

	// 8. Advisory Logic
	advice := advisoryList[cmd]

	return advice, nil
}
