package parser

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"
	"time"
)

var (
	// ErrTerminationRequested indicates that the agent has signaled completion.
	ErrTerminationRequested = errors.New("termination requested by agent")
)

// AgentMetrics contains aggregated data from an agent run.
type AgentMetrics struct {
	Result              string         `json:"result"`
	InputTokens         int            `json:"input_tokens"`
	OutputTokens        int            `json:"output_tokens"`
	TotalTokens         int            `json:"total_tokens"`
	ToolCalls           []ToolCall     `json:"tool_calls"`
	TotalToolCallsCount int            `json:"total_tool_calls_count"`
	FailedToolCalls     int            `json:"failed_tool_calls"`
	Errors              []ErrorEvent   `json:"errors"`
	Messages            []MessageEvent `json:"messages"`
	LoopDetected        bool           `json:"loop_detected"`
}

// ToolCall represents a single tool execution attempt.
type ToolCall struct {
	Name      string        `json:"name"`
	Args      string        `json:"args"`
	Status    string        `json:"status"` // "success" or "error"
	Output    string        `json:"output"`
	Error     string        `json:"error"`
	Duration  time.Duration `json:"duration"`
	Timestamp time.Time     `json:"timestamp"`
}

// ErrorEvent captures error/warning events
type ErrorEvent struct {
	Timestamp time.Time
	Severity  string // "error", "warning", etc.
	Message   string
}

// MessageEvent captures agent message events
type MessageEvent struct {
	Timestamp time.Time `json:"timestamp"`
	Role      string    `json:"role"`
	Content   string    `json:"content"`
	Delta     bool      `json:"delta"`
}

// GeminiEvent represents the generic structure of a streaming event.
type GeminiEvent struct {
	Type      string                 `json:"type"`
	Timestamp string                 `json:"timestamp"`
	ToolName  string                 `json:"tool_name,omitempty"`
	ToolID    string                 `json:"tool_id,omitempty"`
	Status    string                 `json:"status,omitempty"`
	Output    string                 `json:"output,omitempty"`     // For tool_result
	Stats     *GeminiStats           `json:"stats,omitempty"`      // For result event
	Params    map[string]interface{} `json:"parameters,omitempty"` // For tool_use
	Error     string                 `json:"error,omitempty"`      // For error/tool_result?
	Severity  string                 `json:"severity,omitempty"`   // For error events
	Message   string                 `json:"message,omitempty"`    // For error/message events
	Role      string                 `json:"role,omitempty"`       // For message events
	Content   string                 `json:"content,omitempty"`    // For message events
	Delta     bool                   `json:"delta,omitempty"`      // For message events
}

type GeminiStats struct {
	TotalTokens  int `json:"total_tokens"`
	InputTokens  int `json:"input_tokens"`
	OutputTokens int `json:"output_tokens"`
}

// ParseEvents reads a jsonl file and extracts metrics.
func ParseEvents(path string) (*AgentMetrics, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("failed to open event log: %w", err)
	}
	defer f.Close()

	metrics := &AgentMetrics{
		ToolCalls: []ToolCall{},
		Errors:    []ErrorEvent{},
		Messages:  []MessageEvent{},
	}

	// We need to correlate tool_use and tool_result by ID
	pendingTools := make(map[string]*ToolCall)

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		if _, err := ParseLine(line, metrics, pendingTools); err != nil {
			continue
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return metrics, nil
}

// ParseLine processes a single JSONL line and updates metrics.
func ParseLine(line string, metrics *AgentMetrics, pendingTools map[string]*ToolCall) (*GeminiEvent, error) {
	if strings.TrimSpace(line) == "" {
		return nil, nil
	}

	var evt GeminiEvent
	if err := json.Unmarshal([]byte(line), &evt); err != nil {
		return nil, err
	}

	ts, _ := time.Parse(time.RFC3339, evt.Timestamp)

	switch evt.Type {
	case "tool_use":
		argsBytes, _ := json.Marshal(evt.Params)
		tc := &ToolCall{
			Name:      evt.ToolName,
			Args:      string(argsBytes),
			Status:    "pending",
			Timestamp: ts,
		}
		pendingTools[evt.ToolID] = tc

		// Inject into conversation thread
		toolMsg := map[string]string{
			"type": "tool_use",
			"name": evt.ToolName,
			"args": string(argsBytes),
		}
		msgBytes, _ := json.Marshal(toolMsg)
		metrics.Messages = append(metrics.Messages, MessageEvent{
			Timestamp: ts,
			Role:      "tool_use",
			Content:   string(msgBytes),
			Delta:     false,
		})

	case "tool_result":
		if tc, ok := pendingTools[evt.ToolID]; ok {
			tc.Status = evt.Status
			tc.Output = evt.Output
			if evt.Status != "success" {
				tc.Error = evt.Output
				metrics.FailedToolCalls++
			}
			tc.Duration = ts.Sub(tc.Timestamp)
			metrics.ToolCalls = append(metrics.ToolCalls, *tc)
			metrics.TotalToolCallsCount++ // Keep count in sync
			delete(pendingTools, evt.ToolID)

			// Inject into conversation thread
			resMsg := map[string]string{
				"type":   "tool_result",
				"status": evt.Status,
				"output": evt.Output,
			}
			resBytes, _ := json.Marshal(resMsg)
			metrics.Messages = append(metrics.Messages, MessageEvent{
				Timestamp: ts,
				Role:      "tool_result",
				Content:   string(resBytes),
				Delta:     false,
			})
		}

	case "result":
		metrics.Result = evt.Status
		if evt.Stats != nil {
			metrics.InputTokens = evt.Stats.InputTokens
			metrics.OutputTokens = evt.Stats.OutputTokens
			metrics.TotalTokens = evt.Stats.TotalTokens
		}

	case "error":
		metrics.Errors = append(metrics.Errors, ErrorEvent{
			Timestamp: ts,
			Severity:  evt.Severity,
			Message:   evt.Message,
		})
		// Check for loop detection
		if strings.Contains(evt.Message, "Loop detected") {
			metrics.LoopDetected = true
		}

	case "message":
		if evt.Delta {
			// Aggregate deltas
			if len(metrics.Messages) > 0 && metrics.Messages[len(metrics.Messages)-1].Role == evt.Role {
				metrics.Messages[len(metrics.Messages)-1].Content += evt.Content
			} else {
				metrics.Messages = append(metrics.Messages, MessageEvent{
					Timestamp: ts,
					Role:      evt.Role,
					Content:   evt.Content,
					Delta:     true,
				})
			}
		} else {
			metrics.Messages = append(metrics.Messages, MessageEvent{
				Timestamp: ts,
				Role:      evt.Role,
				Content:   evt.Content,
				Delta:     false,
			})
		}

		// Check for termination token in the content
		// Check for termination token in the content
		// Only check if it comes from the model/assistant, to avoid self-triggering on echoed prompts.
		if (evt.Role == "model" || evt.Role == "assistant") && strings.Contains(evt.Content, "<<TENKAI_DONE>>") {
			return &evt, ErrTerminationRequested
		}
	}
	return &evt, nil
}
