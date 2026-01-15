package master

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"

	"github.com/danicat/godoctor/internal/toolnames"
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
	def := toolnames.Registry["agent.master"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
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

	prompt := fmt.Sprintf(`You are the Master Gopher, a wise and slightly witty Go programming expert.
The user has a problem: "%s"

You have access to the following toolkit (currently locked). Use this reference to guide the user:

%s

Your goal is to:
1. Select the best subset of tools to help the user solve their problem.
2. ENABLE those tools for the user.
3. Provide a response that explains WHY you chose those tools.
4. Provide **Recommended Next Steps** with concrete examples of how to call the selected tools to solve the specific problem. Use the usage patterns from the toolkit reference.

Output JSON format:
{
  "selected_tools": ["tool_external_name1", "tool_external_name2"],
  "instructions": "Markdown text with explanation and code blocks showing exactly how to call the tools for this specific task."
}
`, args.Query, formatToolListFromRegistry())

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

func formatToolListFromRegistry() string {
	var sb strings.Builder
	var tools []toolnames.ToolDef
	for _, t := range toolnames.Registry {
		if t.InternalName == "agent.master" {
			continue
		}
		tools = append(tools, t)
	}

	sort.Slice(tools, func(i, j int) bool {
		return tools[i].ExternalName < tools[j].ExternalName
	})

	for _, t := range tools {
		sb.WriteString(t.Instruction + "\n")
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
