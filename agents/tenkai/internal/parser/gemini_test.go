package parser

import (
	"encoding/json"
	"testing"
	"time"
)

func TestMetricCalculation(t *testing.T) {
	// Simulate a log stream with:
	// 1. Tool Use A
	// 2. Tool Result A (Success)
	// 3. Tool Use B
	// 4. Tool Result B (Error)
	// 5. Tool Use C
	// 6. Tool Result C (Error)

	now := time.Now().Format(time.RFC3339)

	events := []GeminiEvent{
		{Type: "init", SessionID: "sess-123", Model: "gemini-1.5-pro", Timestamp: now},
		{Type: "tool_use", ToolID: "id-a", ToolName: "tool_a", Timestamp: now},
		{Type: "tool_result", ToolID: "id-a", Status: "success", Timestamp: now},
		{Type: "tool_use", ToolID: "id-b", ToolName: "tool_b", Timestamp: now},
		{Type: "tool_result", ToolID: "id-b", Status: "error", Output: "failed b", Timestamp: now},
		{Type: "tool_use", ToolID: "id-c", ToolName: "tool_c", Timestamp: now},
		{Type: "tool_result", ToolID: "id-c", Status: "error", Output: "failed c", Timestamp: now},
	}

	metrics := &AgentMetrics{
		ToolCalls: []ToolCall{},
	}
	pendingTools := make(map[string]*ToolCall)

	for _, evt := range events {
		line, _ := json.Marshal(evt)
		if _, err := ParseLine(string(line), metrics, pendingTools); err != nil {
			t.Fatalf("ParseLine failed: %v", err)
		}
	}

	if len(metrics.ToolCalls) != 3 {
		t.Errorf("Expected 3 tool calls, got %d", len(metrics.ToolCalls))
	}

	// Check Counts (Assuming TotalToolCallsCount logic I added relies on len(ToolCalls) or explicit increment)
	// In my implementation, I explicitly incremented TotalToolCallsCount in ParseLine.
	// But let's check the struct field I added.

	if metrics.TotalToolCallsCount != 3 {
		t.Errorf("Expected TotalToolCallsCount=3, got %d", metrics.TotalToolCallsCount)
	}

	if metrics.FailedToolCalls != 2 {
		t.Errorf("Expected FailedToolCalls=2, got %d", metrics.FailedToolCalls)
	}

	if metrics.SessionID != "sess-123" {
		t.Errorf("Expected SessionID='sess-123', got '%s'", metrics.SessionID)
	}
	if metrics.ModelName != "gemini-1.5-pro" {
		t.Errorf("Expected ModelName='gemini-1.5-pro', got '%s'", metrics.ModelName)
	}
}
