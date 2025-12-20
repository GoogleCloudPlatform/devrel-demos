package prompts

import (
	"context"
	"fmt"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const seoPrompt = `**Objective: SEO Audit**

You are an SEO expert. Your task is to audit the content for technical SEO best practices using the ` + "`audit_seo`" + ` tool.

**Instructions:**

1.  **Identify the Source:**
    *   If a URL was provided in the arguments, use that URL.
    *   If no URL was provided, use the most recent, complete text block you generated in this session (treat it as the HTML content).

2.  **Target Keyword:**
    *   If a keyword was provided, use it to check for keyword optimization.

3.  **Action:**
    *   Call the ` + "`audit_seo`" + ` tool with the appropriate parameters (` + "`url`" + ` or ` + "`html`" + `, and ` + "`keyword`" + `).

4.  **Report:**
    *   Present the score and a summary of the findings.
    *   Highlight any "fail" or "warning" items.
    *   Provide specific, actionable advice to improve the score.
`

func SEO() *mcp.Prompt {
	return &mcp.Prompt{
		Name:        "seo",
		Description: "Analyzes a URL or the current text for SEO best practices.",
		Arguments: []*mcp.PromptArgument{
			{
				Name:        "url",
				Description: "The URL to analyze (optional).",
				Required:    false,
			},
			{
				Name:        "keyword",
				Description: "The target keyword to check for (optional).",
				Required:    false,
			},
		},
	}
}

func SEOHandler(ctx context.Context, req *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
	urlArg := req.Params.Arguments["url"]
	keywordArg := req.Params.Arguments["keyword"]

	contextInfo := ""
	if urlArg != "" {
		contextInfo += fmt.Sprintf("\n**Target URL:** %s", urlArg)
	} else {
		contextInfo += "\n**Target Source:** Current Context (Work-in-Progress Text)"
	}

	if keywordArg != "" {
		contextInfo += fmt.Sprintf("\n**Target Keyword:** %s", keywordArg)
	}

	return &mcp.GetPromptResult{
		Messages: []*mcp.PromptMessage{
			{
				Role: "user",
				Content: &mcp.TextContent{
					Text: seoPrompt + contextInfo,
				},
			},
		},
	}, nil
}
