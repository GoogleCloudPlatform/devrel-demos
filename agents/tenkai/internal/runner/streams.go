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

// StreamState encapsulates the state and synchronization for execution streams.
type StreamState struct {
	JobID         string
	Res           *Result
	Cmd           *exec.Cmd
	StreamWg      *sync.WaitGroup
	StdoutMu      *sync.Mutex
	CurrentStdout *strings.Builder
	StderrMu      *sync.Mutex
	CurrentStderr *strings.Builder
	ExecCancel    context.CancelFunc

	// Protected flags
	mu                   sync.Mutex
	terminationRequested bool
	resultFound          bool
}

func (s *StreamState) SetTerminationRequested(v bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.terminationRequested = v
}

func (s *StreamState) IsTerminationRequested() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.terminationRequested
}

func (s *StreamState) SetResultFound(v bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.resultFound = v
}

func (s *StreamState) IsResultFound() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.resultFound
}

func (r *Runner) streamPromptContents(promptPath string, stdinPipe io.WriteCloser) {
	defer stdinPipe.Close()
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

	instruction := "\n\nSYSTEM: Perform the requested task above. When you have FULLY completed the user request (including all verification steps), you MUST output the token '<<TENKAI_DONE>>' to signal completion. Do not output this token before the work is done.\n"
	if _, err := io.WriteString(stdinPipe, instruction); err != nil {
		log.Printf("Warning: failed to write termination instruction to stdin: %v", err)
	}
}

func (r *Runner) streamStdout(stdoutPipe io.ReadCloser, logFile io.Writer, s *StreamState) {
	defer s.StreamWg.Done()
	scanner := bufio.NewScanner(stdoutPipe)
	buf := make([]byte, 0, 10*1024*1024)
	scanner.Buffer(buf, 10*1024*1024)

	if s.Res.AgentMetrics == nil {
		s.Res.AgentMetrics = &parser.AgentMetrics{}
	}
	metrics := s.Res.AgentMetrics

	pendingTools := make(map[string]*parser.ToolCall)
	var lastToolCount int
	var resultSaved bool

	for scanner.Scan() {
		line := scanner.Text()
		fmt.Fprintln(logFile, line)

		s.StdoutMu.Lock()
		s.CurrentStdout.WriteString(line + "\n")
		s.StdoutMu.Unlock()

		evt, err := parser.ParseLine(line, metrics, pendingTools)
		if err != nil && errors.Is(err, parser.ErrTerminationRequested) {
			log.Printf("[Runner] Termination token detected for %s. Requesting graceful shutdown.", s.JobID)
			s.SetTerminationRequested(true)
			go func() {
				time.Sleep(2 * time.Second)
				if s.Cmd.Process != nil {
					if err := s.Cmd.Process.Signal(os.Interrupt); err != nil {
						log.Printf("[Runner] Failed to send SIGINT to %s: %v", s.JobID, err)
					}
				}
			}()
		}

		if evt != nil {
			if s.Res.RunID != 0 {
				if len(metrics.ToolCalls) > lastToolCount {
					newTools := metrics.ToolCalls[lastToolCount:]
					for _, tc := range newTools {
						if err := r.db.SaveRunEvent(s.Res.RunID, "tool", tc); err != nil {
							log.Printf("[Runner] Failed to save tool metrics for %s: %v", s.JobID, err)
						}
					}
					lastToolCount = len(metrics.ToolCalls)
				}
				if err := r.db.SaveRunEvent(s.Res.RunID, evt.Type, evt); err != nil {
					log.Printf("[Runner] Failed to save event %s for %s: %v", evt.Type, s.JobID, err)
				}
			}
			if !resultSaved && metrics.Result != "" {
				resultSaved = true
				log.Printf("[Runner] Result detected for %s. Triggering early exit.", s.JobID)
				s.SetResultFound(true)
				s.ExecCancel()
			}
		}
	}
	if err := scanner.Err(); err != nil {
		log.Printf("[Runner] Error scanning stdout for %s: %v", s.JobID, err)
	}
}

func (r *Runner) streamStderr(stderrPipe io.ReadCloser, stderrFile io.Writer, s *StreamState) {
	defer s.StreamWg.Done()
	scanner := bufio.NewScanner(stderrPipe)
	buf := make([]byte, 0, 10*1024*1024)
	scanner.Buffer(buf, 10*1024*1024)

	for scanner.Scan() {
		line := scanner.Text()
		fmt.Fprintln(stderrFile, line)

		s.StderrMu.Lock()
		s.CurrentStderr.WriteString(line + "\n")
		s.StderrMu.Unlock()

		if s.Res.RunID != 0 && strings.TrimSpace(line) != "" {
			now := time.Now()
			errEvt := &parser.GeminiEvent{
				Type:      "error",
				Timestamp: now.Format(time.RFC3339),
				Severity:  "error",
				Message:   line,
			}
			if err := r.db.SaveRunEvent(s.Res.RunID, "error", errEvt); err != nil {
				log.Printf("[Runner] Failed to save stderr event for run %d: %v", s.Res.RunID, err)
			}
		}
	}
	if err := scanner.Err(); err != nil {
		log.Printf("[Runner] Error scanning stderr: %v", err)
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