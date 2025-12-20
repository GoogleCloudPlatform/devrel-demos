// Package prompts defines the prompts available in the MCP server.
package prompts

import (
	"context"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const importThisPrompt = `Your mission is to read the following documents:
https://go.dev/doc/effective_go
https://go.dev/wiki/CodeReviewComments
https://google.github.io/styleguide/go/
https://go.dev/doc/modules/layout
https://www.ardanlabs.com/blog/2017/02/package-oriented-design.html
https://go-proverbs.github.io/
https://grafana.com/blog/2024/02/09/how-i-write-http-services-in-go-after-13-years/

And produce a comprehensive set of instructions for LLMs to code Go in an idiomatic,
maintainable, testable and easy to read way.`

// ImportThis creates the definition for the 'import_this' prompt.
func ImportThis(namespace string) *mcp.Prompt {
	name := "import_this"
	if namespace != "" {
		name = namespace + ":" + name
	}
	return &mcp.Prompt{
		Name:        name,
		Description: "This is not the Zen of Python, but it will help you write good code.",
		Arguments:   nil,
	}
}

// ImportThisHandler is the handler that generates the content for the 'import_this' prompt.
func ImportThisHandler(_ context.Context, _ *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
	return &mcp.GetPromptResult{
		Messages: []*mcp.PromptMessage{
			{
				Role: "user",
				Content: &mcp.TextContent{
					Text: importThisPrompt,
				},
			},
		},
	}, nil
}
