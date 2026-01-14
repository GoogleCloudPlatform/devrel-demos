package master_gopher

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/modelcontextprotocol/go-sdk/mcp"
	"google.golang.org/genai"
)

// ToolUpdater is a function that updates the allowed tools list.
type ToolUpdater func(tools []string) error

// Register registers the tool with the server.
func Register(server *mcp.Server, updater ToolUpdater) {
	handler := &Handler{
		updater: updater,
	}
	mcp.AddTool(server, &mcp.Tool{
		Name:        "ask_the_master_gopher",
		Title:       "Ask The Master Gopher",
		Description: "Consult the Master Gopher for guidance. Use this when you are unsure which tool to use or how to solve a problem. The Master will review your request, unlock appropriate capabilities in the server, and give you wise instructions.",
	}, handler.Handle)
}

type Handler struct {
	updater ToolUpdater
}

type Params struct {
	Query string `json:"query" jsonschema:"The problem you need help with"`
}

func (h *Handler) Handle(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.Query == "" {
		return &mcp.CallToolResult{IsError: true, Content: []mcp.Content{&mcp.TextContent{Text: "The Master Gopher requires a query to ponder."}}}, nil, nil
	}

	client, err := createGenAIClient(ctx)
	if err != nil {
		return &mcp.CallToolResult{IsError: true, Content: []mcp.Content{&mcp.TextContent{Text: fmt.Sprintf("The Master Gopher is asleep (failed to init AI): %v", err)}}}, nil, nil
	}

	// Definition of all available tools (except this one, and oracle)
	availableTools := []struct {
		Name string
		Desc string
	}{
		{"code_outline", "Get file skeleton and imports"},
		{"inspect_symbol", "Deep dive into symbol implementation"},
		{"read_docs", "Read package documentation (Markdown/JSON)"},
		{"smart_edit", "Intelligently edit code with fuzzy matching"},
		{"list_files", "List directory contents recursively"},
		{"go_build", "Compile project"},
		{"go_test", "Run tests"},
		{"rename_symbol", "Safe semantic renaming"},
		{"analyze_dependency_updates", "Check for breaking dependency changes"},
		{"modernize", "Modernize Go code patterns"},
	}

	prompt := fmt.Sprintf(`You are the Master Gopher, a wise and slightly witty Go programming expert.
The user has a problem: "%s"

You have access to the following toolkit (currently locked):
%s

Your goal is to:
1. Select the best subset of tools to help the user solve their problem.
2. ENABLE those tools for the user.
3. Provide a response that explains WHY you chose those tools and HOW the user (an AI agent) should use them to solve the problem.
4. Be helpful, concise, and maybe a little "pun-y" (use Go puns).

Output JSON format:
{
  "selected_tools": ["tool_name1", "tool_name2"],
  "instructions": "Your wise instructions here..."
}
`, args.Query, formatToolList(availableTools))

	resp, err := client.Models.GenerateContent(ctx, "gemini-2.5-pro", []*genai.Content{
		{Parts: []*genai.Part{{Text: prompt}}},
	}, &genai.GenerateContentConfig{
		ResponseMIMEType: "application/json",
	})
	if err != nil {
		return &mcp.CallToolResult{IsError: true, Content: []mcp.Content{&mcp.TextContent{Text: fmt.Sprintf(" The Master Gopher is confused: %v", err)}}}, nil, nil
	}

	if len(resp.Candidates) == 0 || len(resp.Candidates[0].Content.Parts) == 0 {
		return &mcp.CallToolResult{IsError: true, Content: []mcp.Content{&mcp.TextContent{Text: "The Master Gopher remains silent."}}}, nil, nil
	}

	part := resp.Candidates[0].Content.Parts[0]
	var result struct {
		SelectedTools []string `json:"selected_tools"`
		Instructions  string   `json:"instructions"`
	}

	if err := json.Unmarshal([]byte(part.Text), &result); err != nil {
		return &mcp.CallToolResult{IsError: true, Content: []mcp.Content{&mcp.TextContent{Text: "The Master Gopher mumbled incomprehensibly (JSON error)."}}}, nil, nil
	}

	// Update the tools!
	// We must include "ask_the_master_gopher" so the user can ask again.
	newTools := append(result.SelectedTools, "ask_the_master_gopher")

	if err := h.updater(newTools); err != nil {
		return &mcp.CallToolResult{IsError: true, Content: []mcp.Content{&mcp.TextContent{Text: fmt.Sprintf("The Master Gopher tried to unlock the tools but the key broke: %v", err)}}}, nil, nil
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: result.Instructions},
		},
	}, nil, nil
}

func formatToolList(tools []struct{ Name, Desc string }) string {
	var sb strings.Builder
	for _, t := range tools {
		sb.WriteString(fmt.Sprintf("- %s: %s\n", t.Name, t.Desc))
	}
	return sb.String()
}

func createGenAIClient(ctx context.Context) (*genai.Client, error) {
	apiKey := os.Getenv("GOOGLE_API_KEY")
	if apiKey == "" {
		apiKey = os.Getenv("GEMINI_API_KEY")
	}
	if apiKey == "" {
		return nil, fmt.Errorf("GOOGLE_API_KEY or GEMINI_API_KEY not set")
	}
	return genai.NewClient(ctx, &genai.ClientConfig{
		APIKey:  apiKey,
		Backend: genai.BackendGeminiAPI,
	})
}
