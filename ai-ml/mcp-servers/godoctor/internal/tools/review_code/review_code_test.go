// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
package review_code

import (
	"context"
	"encoding/json"
	"errors"

	"fmt"
	"os"
	"strings"
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
	"google.golang.org/genai"
)

// mockGenerator is a mock implementation of the ContentGenerator interface.
type mockGenerator struct {
	GenerateContentFunc func(ctx context.Context, model string, contents []*genai.Content,
		config *genai.GenerateContentConfig) (*genai.GenerateContentResponse, error)
}

func (m *mockGenerator) GenerateContent(ctx context.Context, model string, contents []*genai.Content,
	config *genai.GenerateContentConfig) (*genai.GenerateContentResponse, error) {
	if m.GenerateContentFunc != nil {
		return m.GenerateContentFunc(ctx, model, contents, config)
	}
	return nil, fmt.Errorf("mockGenerator.GenerateContent: GenerateContentFunc not implemented")
}

func newTestHandler(t *testing.T, mockResponse string) *Handler {
	t.Helper()
	generator := &mockGenerator{
		GenerateContentFunc: func(_ context.Context, _ string, _ []*genai.Content,
			_ *genai.GenerateContentConfig) (*genai.GenerateContentResponse, error) {
			if strings.Contains(mockResponse, "error") {
				return nil, fmt.Errorf("%s", mockResponse)
			}
			return &genai.GenerateContentResponse{
				Candidates: []*genai.Candidate{
					{
						Content: &genai.Content{
							Parts: []*genai.Part{
								{Text: mockResponse},
							},
						},
					},
				},
			}, nil
		},
	}

	// We use WithGenerator to bypass the real client creation
	handler, err := NewHandler(context.Background(), "gemini-2.5-pro", WithGenerator(generator))
	if err != nil {
		t.Fatalf("failed to create test handler: %v", err)
	}
	return handler
}

func unsetEnv(t *testing.T, key string) {
	t.Helper()
	if err := os.Unsetenv(key); err != nil {
		t.Fatalf("failed to unset env var %s: %v", key, err)
	}
}

func setEnv(t *testing.T, key, value string) {
	t.Helper()
	if err := os.Setenv(key, value); err != nil {
		t.Fatalf("failed to set env var %s: %v", key, err)
	}
}

func TestNewHandler_NoAuth(t *testing.T) {
	// Ensure no auth env vars are set for this test
	unsetEnv(t, "GOOGLE_API_KEY")
	unsetEnv(t, "GEMINI_API_KEY")
	unsetEnv(t, "GOOGLE_GENAI_USE_VERTEXAI")
	unsetEnv(t, "GOOGLE_CLOUD_PROJECT")
	unsetEnv(t, "GOOGLE_CLOUD_LOCATION")

	_, err := NewHandler(context.Background(), "gemini-2.5-pro")
	if err == nil {
		t.Fatal("expected an error when creating a handler with no auth, but got nil")
	}
	if !errors.Is(err, ErrAuthFailed) {
		t.Errorf("expected error to be ErrAuthFailed, but got: %v", err)
	}
}

func TestNewHandler_VertexAI_MissingConfig(t *testing.T) {
	// Set Vertex AI flag but unset config
	setEnv(t, "GOOGLE_GENAI_USE_VERTEXAI", "true")
	unsetEnv(t, "GOOGLE_CLOUD_PROJECT")
	unsetEnv(t, "GOOGLE_CLOUD_LOCATION")
	defer unsetEnv(t, "GOOGLE_GENAI_USE_VERTEXAI")

	_, err := NewHandler(context.Background(), "gemini-2.5-pro")
	if err == nil {
		t.Fatal("expected an error when creating a handler with Vertex AI enabled but missing config, but got nil")
	}
	if !errors.Is(err, ErrVertexAIMissingConfig) {
		t.Errorf("expected error to be ErrVertexAIMissingConfig, but got: %v", err)
	}
}

func TestTool_Success(t *testing.T) {
	// 1. Setup
	expectedSuggestions := []ReviewSuggestion{
		{LineNumber: 1, Finding: "Testing", Comment: "This is a test", Severity: "suggestion"},
	}
	mockResponse, err := json.Marshal(expectedSuggestions)
	if err != nil {
		t.Fatalf("failed to marshal mock response: %v", err)
	}
	handler := newTestHandler(t, string(mockResponse))

	// 2. Act
	params := Params{FileContent: "package main"}
	result, reviewResult, err := handler.Tool(context.Background(), nil, params)
	if err != nil {
		t.Fatalf("Tool failed: %v", err)
	}

	// 3. Assert
	if result.IsError {
		t.Fatalf("Expected a successful result, but got an error: %v", result.Content)
	}

	// Verify structured output (ReviewResult)
	if reviewResult == nil {
		t.Fatal("Expected non-nil ReviewResult")
	}
	if len(reviewResult.Suggestions) != 1 || reviewResult.Suggestions[0].Comment != "This is a test" {
		t.Errorf("Unexpected suggestions in ReviewResult: %+v", reviewResult.Suggestions)
	}

	// Verify Markdown output (TextContent)
	textContent, ok := result.Content[0].(*mcp.TextContent)
	if !ok {
		t.Fatalf("Expected TextContent, but got %T", result.Content[0])
	}

	// Check for Markdown headers/content
	if !strings.Contains(textContent.Text, "## Code Review") {
		t.Errorf("Expected Markdown header '## Code Review', but got: %s", textContent.Text)
	}
	if !strings.Contains(textContent.Text, "Found 1 issues") {
		t.Errorf("Expected 'Found 1 issues', but got: %s", textContent.Text)
	}
	if !strings.Contains(textContent.Text, "💡") { // Check for icon
		t.Errorf("Expected icon '💡', but got: %s", textContent.Text)
	}
}

func TestTool_Hint(t *testing.T) {
	// 1. Setup
	expectedSuggestions := []ReviewSuggestion{
		{LineNumber: 1, Finding: "Hint", Comment: "This is a hint test", Severity: "suggestion"},
	}
	mockResponse, err := json.Marshal(expectedSuggestions)
	if err != nil {
		t.Fatalf("failed to marshal mock response: %v", err)
	}
	handler := newTestHandler(t, string(mockResponse))

	// 2. Act
	params := Params{
		FileContent: "package main",
		Hint:        "focus on hints",
	}
	result, reviewResult, err := handler.Tool(context.Background(), nil, params)
	if err != nil {
		t.Fatalf("Tool failed: %v", err)
	}

	// 3. Assert
	if result.IsError {
		t.Fatalf("Expected a successful result, but got an error: %v", result.Content)
	}

	// Verify structured output
	if reviewResult == nil {
		t.Fatal("Expected non-nil ReviewResult")
	}
	if len(reviewResult.Suggestions) != 1 || reviewResult.Suggestions[0].Comment != "This is a hint test" {
		t.Errorf("Unexpected suggestions in ReviewResult: %+v", reviewResult.Suggestions)
	}

	textContent, ok := result.Content[0].(*mcp.TextContent)
	if !ok {
		t.Fatalf("Expected TextContent, but got %T", result.Content[0])
	}

	if !strings.Contains(textContent.Text, "## Code Review") {
		t.Errorf("Expected Markdown output, but got: %s", textContent.Text)
	}
}

func TestTool_InvalidJSON(t *testing.T) {
	// 1. Setup
	handler := newTestHandler(t, "this is not json")

	// 2. Act
	params := Params{FileContent: "package main"}
	result, _, err := handler.Tool(context.Background(), nil, params)
	if err != nil {
		t.Fatalf("Tool returned an unexpected error: %v", err)
	}

	// 3. Assert
	if !result.IsError {
		t.Fatal("Expected an error result, but got a successful one")
	}
	textContent, ok := result.Content[0].(*mcp.TextContent)
	if !ok {
		t.Fatalf("Expected TextContent, but got %T", result.Content[0])
	}
	if !strings.Contains(textContent.Text, "failed to parse model response") {
		t.Errorf("Expected a parse error, but got: %s", textContent.Text)
	}
}
