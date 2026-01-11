package parser

import (
	"encoding/json"
	"testing"
	"time"
)

func TestTokenParsing(t *testing.T) {
	now := time.Now().Format(time.RFC3339)

	// Simulate a result event with stats
	evt := GeminiEvent{
		Type:      "result",
		Status:    "success",
		Timestamp: now,
		Stats: &GeminiStats{
			TotalTokens:  1234,
			InputTokens:  1000,
			OutputTokens: 234,
		},
	}

	metrics := &AgentMetrics{}
	pendingTools := make(map[string]*ToolCall)

	line, _ := json.Marshal(evt)
	if _, err := ParseLine(string(line), metrics, pendingTools); err != nil {
		t.Fatalf("ParseLine failed: %v", err)
	}

	if metrics.TotalTokens != 1234 {
		t.Errorf("Expected TotalTokens=1234, got %d", metrics.TotalTokens)
	}
	if metrics.InputTokens != 1000 {
		t.Errorf("Expected InputTokens=1000, got %d", metrics.InputTokens)
	}
	if metrics.OutputTokens != 234 {
		t.Errorf("Expected OutputTokens=234, got %d", metrics.OutputTokens)
	}
	if metrics.Result != "success" {
		t.Errorf("Expected Result='success', got %s", metrics.Result)
	}
}
