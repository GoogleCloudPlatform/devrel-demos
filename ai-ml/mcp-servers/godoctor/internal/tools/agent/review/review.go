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
// Package review_code implements the AI-powered code review tool.
package review

import (
	"context"
	"encoding/json"
	"fmt"

	"log"
	"os"
	"regexp"
	"strings"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"google.golang.org/genai"
)

var (
	// ErrVertexAIMissingConfig indicates that Vertex AI is enabled but project/location configuration is missing.
	ErrVertexAIMissingConfig = fmt.Errorf("vertex AI enabled but missing configuration")

	// ErrAuthFailed indicates that no valid authentication credentials were found.
	ErrAuthFailed = fmt.Errorf("authentication failed")
)

// Register registers the code_review tool with the server.
func Register(server *mcp.Server, defaultModel string) {
	reviewHandler, err := NewHandler(context.Background(), defaultModel)
	if err != nil {
		log.Printf("Disabling code_review tool: failed to create handler: %v", err)
		return
	}
	def := toolnames.Registry["agent.review"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, reviewHandler.Tool)
}

// Params defines the input parameters for the code_review tool.
type Params struct {
	FileContent string `json:"file_content"`
	ModelName   string `json:"model_name,omitempty"`
	Hint        string `json:"hint,omitempty"`
}

// ReviewSuggestion defines the structured output for a single review suggestion.
type ReviewSuggestion struct {
	LineNumber int    `json:"line_number"`
	Severity   string `json:"severity"` // "error", "warning", "suggestion"
	Finding    string `json:"finding"`
	Comment    string `json:"comment"`
}

// ReviewResult defines the structured output for the code_review tool.
type ReviewResult struct {
	Suggestions []ReviewSuggestion `json:"suggestions"`
}

// ContentGenerator abstracts the generative model for testing.
type ContentGenerator interface {
	GenerateContent(ctx context.Context, model string, contents []*genai.Content,
		config *genai.GenerateContentConfig) (*genai.GenerateContentResponse, error)
}

// RealGenerator wraps the actual GenAI client.
type RealGenerator struct {
	client *genai.Client
}

// GenerateContent generates content using the underlying GenAI client.
func (r *RealGenerator) GenerateContent(ctx context.Context, model string, contents []*genai.Content,
	config *genai.GenerateContentConfig) (*genai.GenerateContentResponse, error) {
	return r.client.Models.GenerateContent(ctx, model, contents, config)
}

// Handler holds the dependencies for the review code tool.
type Handler struct {
	generator    ContentGenerator
	defaultModel string
}

// Option is a function that configures a Handler.
type Option func(*Handler)

// WithGenerator sets the ContentGenerator for the Handler.
func WithGenerator(generator ContentGenerator) Option {
	return func(h *Handler) {
		h.generator = generator
	}
}

// NewHandler creates a new Handler.
func NewHandler(ctx context.Context, defaultModel string, opts ...Option) (*Handler, error) {
	handler := &Handler{
		defaultModel: defaultModel,
	}
	for _, opt := range opts {
		opt(handler)
	}

	if handler.generator == nil {
		var config *genai.ClientConfig

		// Check if Vertex AI is explicitly requested
		useVertex := os.Getenv("GOOGLE_GENAI_USE_VERTEXAI")
		if useVertex == "true" || useVertex == "1" {
			project := os.Getenv("GOOGLE_CLOUD_PROJECT")
			location := os.Getenv("GOOGLE_CLOUD_LOCATION")

			if project == "" || location == "" {
				return nil, fmt.Errorf("%w: set GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION", ErrVertexAIMissingConfig)
			}

			config = &genai.ClientConfig{
				Project:  project,
				Location: location,
				Backend:  genai.BackendVertexAI,
			}
		} else {
			// Default to Gemini API
			apiKey := os.Getenv("GOOGLE_API_KEY")
			if apiKey == "" {
				apiKey = os.Getenv("GEMINI_API_KEY")
			}

			if apiKey == "" {
				return nil, fmt.Errorf("%w: set GOOGLE_API_KEY (or GEMINI_API_KEY) "+
					"for Gemini API, or set GOOGLE_GENAI_USE_VERTEXAI=true with GOOGLE_CLOUD_PROJECT "+
					"and GOOGLE_CLOUD_LOCATION for Vertex AI", ErrAuthFailed)
			}

			config = &genai.ClientConfig{
				APIKey:  apiKey,
				Backend: genai.BackendGeminiAPI,
			}
		}

		client, err := genai.NewClient(ctx, config)
		if err != nil {
			return nil, fmt.Errorf("failed to create genai client: %w", err)
		}
		handler.generator = &RealGenerator{client: client}
	}
	return handler, nil
}

var jsonMarkdownRegex = regexp.MustCompile("(?s)```json" + "\\s*(.*?)" + "```")

// Tool performs an AI-powered code review and returns structured data.
func (h *Handler) Tool(ctx context.Context, _ *mcp.CallToolRequest, args Params) (
	*mcp.CallToolResult, *ReviewResult, error) {
	if args.FileContent == "" {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: "file_content cannot be empty"},
			},
		}, nil, nil
	}

	modelName := h.defaultModel
	if args.ModelName != "" {
		modelName = args.ModelName
	}

	systemPrompt := constructSystemPrompt(args.Hint)

	// Construct the request using the new SDK
	contents := []*genai.Content{
		{
			Parts: []*genai.Part{
				{Text: systemPrompt},
				{Text: args.FileContent},
			},
		},
	}

	resp, err := h.generator.GenerateContent(ctx, modelName, contents, nil)
	if err != nil {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: fmt.Sprintf("failed to generate content: %v", err)},
			},
		}, nil, nil
	}

	return h.processResponse(resp)
}

func (h *Handler) processResponse(resp *genai.GenerateContentResponse) (*mcp.CallToolResult, *ReviewResult, error) {
	if !isValidResponse(resp) {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: "no response content from model. Check model parameters and API status"},
			},
		}, nil, nil
	}

	// Extract text from the first part of the first candidate
	part := resp.Candidates[0].Content.Parts[0]
	if part.Text == "" {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: "unexpected response format from model, expected text content"},
			},
		}, nil, nil
	}

	suggestions, err := parseReviewResponse(part.Text)
	if err != nil {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: fmt.Sprintf("failed to parse model response: %v", err)},
			},
		}, nil, nil
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: renderReviewMarkdown(suggestions)},
		},
	}, &ReviewResult{Suggestions: suggestions}, nil
}

func parseReviewResponse(text string) ([]ReviewSuggestion, error) {
	// Clean the response by trimming markdown and whitespace
	cleanedJSON := jsonMarkdownRegex.ReplaceAllString(text, "$1")

	var suggestions []ReviewSuggestion
	if err := json.Unmarshal([]byte(cleanedJSON), &suggestions); err != nil {
		return nil, fmt.Errorf("failed to unmarshal suggestions: %w", err)
	}
	return suggestions, nil
}

func renderReviewMarkdown(suggestions []ReviewSuggestion) string {
	if len(suggestions) == 0 {
		return "## Code Review\n\nNo issues found. Great job! 🚀"
	}

	var buf strings.Builder
	buf.WriteString(fmt.Sprintf("## Code Review\n\nFound %d issues.\n\n", len(suggestions)))

	for _, s := range suggestions {
		icon := "ℹ️"
		switch strings.ToLower(s.Severity) {
		case "error":
			icon = "🚨"
		case "warning":
			icon = "⚠️"
		case "suggestion":
			icon = "💡"
		}

		buf.WriteString(fmt.Sprintf("### %s Line %d: %s\n", icon, s.LineNumber, s.Finding))
		buf.WriteString(fmt.Sprintf("**Severity:** %s\n\n", s.Severity))
		buf.WriteString(s.Comment)
		buf.WriteString("\n\n---\n\n")
	}
	return buf.String()
}

func isValidResponse(resp *genai.GenerateContentResponse) bool {
	return resp != nil && len(resp.Candidates) > 0 &&
		resp.Candidates[0].Content != nil && len(resp.Candidates[0].Content.Parts) > 0
}

func constructSystemPrompt(hint string) string {
	prompt := `You are an expert Go code reviewer. Your goal is to help the developer improve their code quality,
safety, and idiomatic style. Be constructive, specific, and prioritize critical issues (bugs, race conditions)
over minor style nitpicks.

**Guidelines:**
1.  **Correctness:** Identify bugs, race conditions, and unhandled errors. (Severity: "error")
2.  **Idioms:** specific Go patterns (e.g., table-driven tests, proper interface usage). (Severity: "warning")
3.  **Simplicity:** Suggest simplifications if code is overly complex. (Severity: "suggestion")
4.  **Style:** Follow effective Go and CodeReviewComments. (Severity: "suggestion")

**Format:**
Return a JSON array of objects. Do not include markdown code blocks around the JSON.
Each object must have:
- "line_number": int
- "severity": "error" | "warning" | "suggestion"
- "finding": string (concise title)
- "comment": string (detailed explanation and recommendation)

If no issues are found, return an empty array: []`

	if hint != "" {
		prompt = fmt.Sprintf("Focus on this hint: \"%s\".\n\n%s", hint, prompt)
	}
	return prompt
}
