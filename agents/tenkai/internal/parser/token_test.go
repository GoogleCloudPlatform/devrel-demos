package parser

import (
	"testing"
)

func TestTokenParsing(t *testing.T) {
	// Simulate a result event with stats (using raw JSON to match CLI output)
	jsonLine := `{"type":"result","timestamp":"2024-01-01T00:00:00Z","status":"success","stats":{"total_tokens":1234,"input_tokens":1000,"output_tokens":234,"cached":50}}`

	metrics := &AgentMetrics{}
	pendingTools := make(map[string]*ToolCall)

	if _, err := ParseLine(jsonLine, metrics, pendingTools); err != nil {
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
	if metrics.CachedTokens != 50 {
		t.Errorf("Expected CachedTokens=50, got %d", metrics.CachedTokens)
	}
	if metrics.Result != "success" {
		t.Errorf("Expected Result='success', got %s", metrics.Result)
	}
}
