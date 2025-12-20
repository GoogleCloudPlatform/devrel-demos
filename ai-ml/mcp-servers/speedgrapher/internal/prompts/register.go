package prompts

import (
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers all prompts with the server.
func Register(server *mcp.Server, editorialGuidelines, localizationGuidelines string) {
	server.AddPrompt(Haiku(), HaikuHandler)
	server.AddPrompt(Interview(), InterviewHandler)
	server.AddPrompt(Localize(), NewLocalizeHandler(localizationGuidelines))
	server.AddPrompt(Review(), NewReviewHandler(editorialGuidelines))
	server.AddPrompt(Reflect(), ReflectHandler)
	server.AddPrompt(Readability(), ReadabilityHandler)
	server.AddPrompt(Context(), ContextHandler)
	server.AddPrompt(Voice(), VoiceHandler)
	server.AddPrompt(Outline(), OutlineHandler)
	server.AddPrompt(Expand(), ExpandHandler)
	server.AddPrompt(Publish(), PublishHandler)
	server.AddPrompt(SEO(), SEOHandler)
}
