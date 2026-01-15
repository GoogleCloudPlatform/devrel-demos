package runner

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/parser"
)

func (r *Runner) streamPromptContents(promptPath string, stdinPipe io.WriteCloser) {
	defer stdinPipe.Close() // Ensure EOF is sent
	// Open the prompt file here to ensure we have a fresh handle
	promptFile, err := os.Open(promptPath)
	if err != nil {
		log.Printf("Warning: failed to open PROMPT.md for streaming: %v", err)
		return
	}
	defer promptFile.Close()

	if _, err := io.Copy(stdinPipe, promptFile); err != nil {
		log.Printf("Warning: failed to copy prompt to stdin: %v", err)
		return
	}

	// Inject termination instruction
	instruction := "\n\nSYSTEM: Perform the requested task above. When you have FULLY completed the user request (including all verification steps), you MUST output the token '<<TENKAI_DONE>>' to signal completion. Do not output this token before the work is done. IMPORTANT: Do not delete any files or directories you created. They are needed for automated validation.\n"
	if _, err := io.WriteString(stdinPipe, instruction); err != nil {
		log.Printf("Warning: failed to write termination instruction to stdin: %v", err)
	}
}

func (r *Runner) streamStdout(stdoutPipe io.Reader, logFile io.Writer, jobID string, res *Result, cmd *exec.Cmd, streamWg *sync.WaitGroup, stdoutMu *sync.Mutex, currentStdout *strings.Builder, terminationRequested *bool, resultFound *bool, resultFoundMu *sync.Mutex, execCancel context.CancelFunc) {
	defer streamWg.Done()
	scanner := bufio.NewScanner(stdoutPipe)

	// Ensure metrics struct exists on the result
	if res.AgentMetrics == nil {
		res.AgentMetrics = &parser.AgentMetrics{}
	}
	metrics := res.AgentMetrics

	pendingTools := make(map[string]*parser.ToolCall)
	var lastToolCount int
	var resultSaved bool

	for scanner.Scan() {
		line := scanner.Text()
		fmt.Fprintln(logFile, line)

		stdoutMu.Lock()
		currentStdout.WriteString(line + "\n")
		stdoutMu.Unlock()

		// Real-time parsing and event emission
		evt, err := parser.ParseLine(line, metrics, pendingTools)
		if err != nil && errors.Is(err, parser.ErrTerminationRequested) {
			// Termination requested by agent
			log.Printf("[Runner] Termination token detected for %s. Requesting graceful shutdown.", jobID)

			*terminationRequested = true

			// TRIGGER GRACEFUL SHUTDOWN (Delayed)
			// Trigger interrupt logic if we have access to the process handle?
			// Since we abstracted execution, we might not have 'cmd' here anymore if we fully removed it.
			// But for now streamStdout signature still has it (unused in cloud run path).
			// If we are in Cloud Run mode, 'cmd' is nil. We can't signal interrupt.
			// We just let it run or rely on execCancel?
			// execCancel will kill it hard.
			// Ideally Executor interface should have a "Signal" method.
			// For now, if cmd is present (LocalExecutor logic might expose it? No, Executor hides it).
			// WE ONLY HAVE execCancel.
			// Let's just create a goroutine to wait a bit then cancel?
			// Actually, termination requested means "I am done". We should just exit logic.

			// We set terminationRequested = true, allowing waitForCommand to treat exit as success.
			// Then we cancel context.
			go func() {
				time.Sleep(2 * time.Second)
				execCancel()
			}()
		}

		if evt != nil {
			if res.RunID != 0 {
				// Check for new tool results
				if len(metrics.ToolCalls) > lastToolCount {
					newTools := metrics.ToolCalls[lastToolCount:]
					for _, tc := range newTools {
						r.db.SaveRunEvent(res.RunID, "tool", tc)
					}
					lastToolCount = len(metrics.ToolCalls)
				}
				// Save EVERY raw event to the database immediately.
				r.db.SaveRunEvent(res.RunID, evt.Type, evt)
			}
			// Check for final result stats (Early Exit)
			if !resultSaved && metrics.Result != "" {
				resultSaved = true
				log.Printf("[Runner] Result detected for %s. Triggering early exit.", jobID)

				resultFoundMu.Lock()
				*resultFound = true
				resultFoundMu.Unlock()

				execCancel()
			}
		}
	}
}

func (r *Runner) streamStderr(stderrPipe io.Reader, stderrFile io.Writer, res *Result, streamWg *sync.WaitGroup, stderrMu *sync.Mutex, currentStderr *strings.Builder) {
	defer streamWg.Done()
	scanner := bufio.NewScanner(stderrPipe)
	for scanner.Scan() {
		line := scanner.Text()
		fmt.Fprintln(stderrFile, line)

		stderrMu.Lock()
		currentStderr.WriteString(line + "\n")
		stderrMu.Unlock()

		if res.RunID != 0 && strings.TrimSpace(line) != "" {
			now := time.Now()
			errEvt := &parser.GeminiEvent{
				Type:      "error",
				Timestamp: now.Format(time.RFC3339),
				Severity:  "error",
				Message:   line,
			}
			r.db.SaveRunEvent(res.RunID, "error", errEvt)
		}
	}
}

func (r *Runner) syncLogs(ctx context.Context, res *Result, stdoutMu *sync.Mutex, currentStdout *strings.Builder, stderrMu *sync.Mutex, currentStderr *strings.Builder) {
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			stdoutMu.Lock()
			out := currentStdout.String()
			stdoutMu.Unlock()
			stderrMu.Lock()
			errStr := currentStderr.String()
			stderrMu.Unlock()
			r.db.UpdateRunLogs(res.RunID, out, errStr)
		}
	}
}
