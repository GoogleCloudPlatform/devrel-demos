package specialist

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/danicat/godoctor/internal/tools/file/list"
	"github.com/danicat/godoctor/internal/tools/file/outline"
	"github.com/danicat/godoctor/internal/tools/go/docs"
	"github.com/danicat/godoctor/internal/tools/go/test"
	"github.com/danicat/godoctor/internal/tools/symbol/inspect"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"google.golang.org/genai"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["agent.specialist"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, toolHandler)
}

type Params struct {
	Query string `json:"query" jsonschema:"The question or task for the specialist"`
}

func toolHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.Query == "" {
		return &mcp.CallToolResult{IsError: true, Content: []mcp.Content{&mcp.TextContent{Text: "query cannot be empty"}}}, nil, nil
	}

	client, err := createGenAIClient(ctx)
	if err != nil {
		return &mcp.CallToolResult{IsError: true, Content: []mcp.Content{&mcp.TextContent{Text: fmt.Sprintf("failed to init AI: %v", err)}}}, nil, nil
	}

	// 1. Define Tools for the Model
	tools := []*genai.Tool{
		{
			FunctionDeclarations: []*genai.FunctionDeclaration{
				{
					Name:        "list_files",
					Description: "List files in directory",
					Parameters: &genai.Schema{
						Type: genai.TypeObject,
						Properties: map[string]*genai.Schema{
							"path":      {Type: genai.TypeString, Description: "Root path"},
							"depth":     {Type: genai.TypeInteger, Description: "Max depth"},
							"recursive": {Type: genai.TypeBoolean, Description: "Recursive list"},
						},
					},
				},
				{
					Name:        "read_docs",
					Description: "Read Go documentation",
					Parameters: &genai.Schema{
						Type: genai.TypeObject,
						Properties: map[string]*genai.Schema{
							"package_path": {Type: genai.TypeString, Description: "Import path e.g. fmt"},
							"symbol_name":  {Type: genai.TypeString, Description: "Symbol name e.g. Println"},
						},
					},
				},
				{
					Name:        "inspect_symbol",
					Description: "Inspect symbol source and signature",
					Parameters: &genai.Schema{
						Type: genai.TypeObject,
						Properties: map[string]*genai.Schema{
							"package": {Type: genai.TypeString, Description: "Package path"},
							"symbol":  {Type: genai.TypeString, Description: "Symbol name"},
							"file":    {Type: genai.TypeString, Description: "Context file path"},
						},
					},
				},
				{
					Name:        "code_outline",
					Description: "Get file outline",
					Parameters: &genai.Schema{
						Type: genai.TypeObject,
						Properties: map[string]*genai.Schema{
							"file": {Type: genai.TypeString, Description: "File path"},
						},
						Required: []string{"file"},
					},
				},
				{
					Name:        "go_test",
					Description: "Run go test",
					Parameters: &genai.Schema{
						Type: genai.TypeObject,
						Properties: map[string]*genai.Schema{
							"dir":      {Type: genai.TypeString, Description: "Directory"},
							"packages": {Type: genai.TypeArray, Items: &genai.Schema{Type: genai.TypeString}, Description: "Packages to test"},
							"run":      {Type: genai.TypeString, Description: "Regex to match tests"},
						},
					},
				},
			},
		},
	}

	// 2. Chat Loop
	// We use max steps to prevent infinite loops
	const maxSteps = 10
	history := []*genai.Content{
		{
			Role: "user",
			Parts: []*genai.Part{
				{Text: fmt.Sprintf("Question: %s\n\nYou are the GoDoctor Specialist. You have access to tools to investigate the codebase. Use them to answer the question. Be concise.", args.Query)},
			},
		},
	}

	for i := 0; i < maxSteps; i++ {
		// Call Model
		resp, err := client.Models.GenerateContent(ctx, "gemini-2.5-pro", history, &genai.GenerateContentConfig{
			Tools: tools,
		})
		if err != nil {
			return errorResult(fmt.Sprintf("LLM error: %v", err)), nil, nil
		}

		if len(resp.Candidates) == 0 || len(resp.Candidates[0].Content.Parts) == 0 {
			break
		}

		cand := resp.Candidates[0]
		part := cand.Content.Parts[0]

		// Add model response to history
		history = append(history, cand.Content)

		// Check for Function Calls
		if len(cand.Content.Parts) > 0 {
			// Iterate parts to find function calls
			var toolOutputs []*genai.Part
			hasCalls := false

			for _, ignoredPart := range cand.Content.Parts {
				// The SDK might have multiple parts? usually one func call per part if parallel calling?
				// Actually genai.Part has FunctionCall field.

				// Let's assume sequential or check parts.
				// Wait, range over parts:
				_ = ignoredPart
			}

			for _, p := range cand.Content.Parts {
				if p.FunctionCall != nil {
					hasCalls = true
					call := p.FunctionCall
					log.Printf("Oracle calling: %s(%v)", call.Name, call.Args)

					// Execute Tool
					result, err := executeTool(ctx, call.Name, call.Args)
					output := ""
					if err != nil {
						output = fmt.Sprintf("Error: %v", err)
					} else {
						// Result is *mcp.CallToolResult.
						// Extract text.
						sb := strings.Builder{}
						for _, c := range result.Content {
							if tc, ok := c.(*mcp.TextContent); ok {
								sb.WriteString(tc.Text)
							}
						}
						output = sb.String()
						// Truncate if too long?
						if len(output) > 20000 {
							output = output[:20000] + "...(truncated)"
						}
					}

					toolOutputs = append(toolOutputs, &genai.Part{
						FunctionResponse: &genai.FunctionResponse{
							Name: call.Name,
							Response: map[string]interface{}{
								"content": output,
							},
						},
					})
				}
			}

			if hasCalls {
				// Send tool outputs back
				history = append(history, &genai.Content{
					Role: "user", // Tool outputs come from user side conceptually in Gemini API? Or "function"? SDK handles roles?
					// In Gemini, role is "function" or "model"?
					// Actually, GenerateContent expects parts.
					// SDK usage: Usually part with FunctionResponse.
					// Role should be "user" or "function"? Gemini API says "function" role isn't distinct, it's about the Part type.
					// But usually "user" sends the result.
					Parts: toolOutputs,
				})
				continue // Loop again
			}
		}

		// No function calls -> Final Answer?
		// If text part exists, that's the answer.
		if part.Text != "" {
			return &mcp.CallToolResult{
				Content: []mcp.Content{
					&mcp.TextContent{Text: part.Text},
				},
			}, nil, nil
		}
	}

	return errorResult("Oracle exceeded max steps without answer."), nil, nil
}

func executeTool(ctx context.Context, name string, args map[string]interface{}) (*mcp.CallToolResult, error) {
	// Helper to marshal args to json then unmarshal to specific struct?
	// Or simplified manual mapping.
	// We reused json marshalling for simplicity in many places.
	jsonBytes, _ := json.Marshal(args)

	switch name {
	case "list_files":
		var p list.Params
		json.Unmarshal(jsonBytes, &p)
		res, _, err := list.Handler(ctx, nil, p)
		return res, err
	case "read_docs":
		var p docs.Params
		json.Unmarshal(jsonBytes, &p)
		res, _, err := docs.Handler(ctx, nil, p)
		return res, err
	case "inspect_symbol":
		var p inspect.Params
		json.Unmarshal(jsonBytes, &p)
		res, _, err := inspect.Handler(ctx, nil, p)
		return res, err
	case "code_outline":
		var p outline.Params
		json.Unmarshal(jsonBytes, &p)
		res, _, err := outline.Handler(ctx, nil, p)
		return res, err
	case "go_test":
		var p test.Params
		json.Unmarshal(jsonBytes, &p)
		res, _, err := test.Handler(ctx, nil, p)
		return res, err
	}
	return nil, fmt.Errorf("unknown tool: %s", name)
}

func createGenAIClient(ctx context.Context) (*genai.Client, error) {
	// Reusing logic from review_code
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

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}
