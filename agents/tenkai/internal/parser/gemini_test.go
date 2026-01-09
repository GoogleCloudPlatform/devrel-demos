package parser

import (
	"testing"
)

func TestParseLine_ReturnsEvent(t *testing.T) {
	metrics := &AgentMetrics{}
	pendingTools := make(map[string]*ToolCall)

	// Test 1: Standard Message (No Delta)
	line := `{"type": "message", "role": "user", "content": "Hello", "timestamp": "2024-01-01T12:00:00Z"}`
	evt, err := ParseLine(line, metrics, pendingTools)
	if err != nil {
		t.Fatalf("ParseLine failed: %v", err)
	}
	if evt == nil {
		t.Fatal("Expected event, got nil")
	}
	if evt.Type != "message" || evt.Content != "Hello" {
		t.Errorf("Unexpected event content: %+v", evt)
	}

	// Test 2: Delta Message
	lineDelta := `{"type": "message", "role": "model", "content": " World", "delta": true, "timestamp": "2024-01-01T12:00:01Z"}`
	evtDelta, err := ParseLine(lineDelta, metrics, pendingTools)
	if err != nil {
		t.Fatalf("ParseLine delta failed: %v", err)
	}
	if !evtDelta.Delta {
		t.Error("Expected delta=true")
	}

	// Test 3: Tool Use (Synthetic Message Injection Check)
	// We want to ensure ParseLine still updates metrics correctly even if we only care about the return event for streaming.
	// But ParseLine ALSO updates the metrics struct passed in.
	lineTool := `{"type": "tool_use", "tool_name": "calc", "tool_id": "call_1", "parameters": {"x": 1}, "timestamp": "2024-01-01T12:00:02Z"}`
	_, err = ParseLine(lineTool, metrics, pendingTools)
	if err != nil {
		t.Fatalf("ParseLine tool failed: %v", err)
	}

	// Check if tool was added to pending
	if _, ok := pendingTools["call_1"]; !ok {
		t.Error("Tool call not pending")
	}
}
