package stylist

import (
	"context"
	_ "embed"
	"encoding/json"
	"fmt"
	"log/slog"
	"slices"
	"strings"

	"goagents/fittingroom"
	"goagents/tools"

	"google.golang.org/adk/agent"
	"google.golang.org/adk/agent/llmagent"
	"google.golang.org/adk/model"
	"google.golang.org/adk/model/gemini"
	"google.golang.org/adk/tool"
	"google.golang.org/adk/tool/agenttool"
	"google.golang.org/adk/tool/loadartifactstool"
	"google.golang.org/genai"
)

//go:embed instructions.md
var instructions string

const stateKeyPreviousProducts = "previously_used_products"
const stateKeyUserImageStr = "user_base_image_str"
const stateKeyUserImageArtifact = "user_base_image_artifact"

// LockUserImageArtifact is a BeforeAgentCallback that captures the artifact
// name of the user's uploaded photo and pins it to session state. This is
// the deterministic anchor for face identity across multi-turn refinement:
// every fitting_tool invocation from this session is steered toward using
// THIS exact artifact as user_image, instead of any other image the LLM
// might find in context (e.g. a previously generated outfit).
//
// Runs after SaveIncomingBlobs (which actually saves the artifacts), so by
// the time this callback fires, the artifact already exists in storage.
func LockUserImageArtifact(ctx agent.CallbackContext) (*genai.Content, error) {
	// If we already have one pinned from an earlier turn, leave it alone —
	// multi-turn refinement should re-use the original, not whatever was
	// uploaded most recently.
	if existing, err := ctx.State().Get(stateKeyUserImageArtifact); err == nil {
		if s, ok := existing.(string); ok && s != "" {
			slog.Info("User base image artifact already pinned to state, keeping", "artifact", s)
			return nil, nil
		}
	}

	// First inline image in the user's message is the base photo.
	contents := ctx.UserContent()
	if contents == nil {
		return nil, nil
	}
	for pindex, p := range contents.Parts {
		if p.InlineData == nil {
			continue
		}
		artifactName := fmt.Sprintf("upload_%s_%d", ctx.InvocationID(), pindex)
		slog.Info("Pinning user base image artifact to state", "artifact", artifactName)
		if err := ctx.State().Set(stateKeyUserImageArtifact, artifactName); err != nil {
			slog.Warn("Failed to pin user image artifact to state", "err", err)
		}
		return nil, nil
	}
	return nil, nil
}

// ExtractAndInjectUserImage is a BeforeModelCallback that keeps the user's
// base image reference available across multi-turn feedback. The reference can
// be either a gs:// URI (from a prior fitting room result, sent by Flutter as
// "User try-on base image" text) OR a pinned artifact name (saved by
// LockUserImageArtifact above when Flutter sends inline bytes).
//
// On the first request, this callback finds the URI in the message and saves
// it to state. On follow-up turns ("make it more casual"), the URI isn't
// re-sent — so the callback retrieves it (or the pinned artifact name) from
// state and re-injects it as an explicit reminder to the LLM, so it routes
// the right input to fitting_tool every time.
func ExtractAndInjectUserImage(ctx agent.CallbackContext, req *model.LLMRequest) (*model.LLMResponse, error) {
	const marker = "User try-on base image"
	var foundURI string

	// Search the latest user message for the marker and extract the gs:// URI.
	for i := len(req.Contents) - 1; i >= 0; i-- {
		if req.Contents[i].Role != "user" {
			continue
		}
		for _, part := range req.Contents[i].Parts {
			if !strings.Contains(part.Text, marker) {
				continue
			}
			idx := strings.Index(part.Text, "gs://")
			if idx < 0 {
				continue
			}
			rest := part.Text[idx:]
			end := len(rest)
			for j, r := range rest {
				if r == ' ' || r == '\n' || r == '\t' {
					end = j
					break
				}
			}
			foundURI = rest[:end]
		}
		break
	}

	if foundURI != "" {
		slog.Info("Saving user base image URI to state", "uri", foundURI)
		if err := ctx.State().Set(stateKeyUserImageStr, foundURI); err != nil {
			slog.Warn("Failed to save user image URI to state", "err", err)
		}
		return nil, nil
	}

	// Prefer a saved gs:// URI if we have one (cross-session reuse path).
	if val, err := ctx.State().Get(stateKeyUserImageStr); err == nil {
		if savedURI, ok := val.(string); ok && savedURI != "" {
			slog.Info("Re-injecting saved user base image URI", "uri", savedURI)
			injectReminder(req, fmt.Sprintf(
				"REMINDER: ALWAYS use this gs:// URI as user_image when calling fitting_tool. Do NOT use any other image. URI: %s",
				savedURI))
			return nil, nil
		}
	}

	// Fall back to the pinned artifact name (inline-upload path).
	if val, err := ctx.State().Get(stateKeyUserImageArtifact); err == nil {
		if savedArt, ok := val.(string); ok && savedArt != "" {
			slog.Info("Re-injecting pinned user base image artifact", "artifact", savedArt)
			injectReminder(req, fmt.Sprintf(
				"REMINDER: ALWAYS use the artifact named %q as user_image when calling fitting_tool. This is the user's original photo. Do NOT use any generated_fitting_* artifact or any other image as user_image — those are outputs, not the source of identity.",
				savedArt))
		}
	}
	return nil, nil
}

func injectReminder(req *model.LLMRequest, text string) {
	for i := len(req.Contents) - 1; i >= 0; i-- {
		if req.Contents[i].Role == "user" {
			req.Contents[i].Parts = append(req.Contents[i].Parts, genai.NewPartFromText(text))
			return
		}
	}
}

// InjectPreviousProducts is a BeforeModelCallback that reads previously selected
// product IDs from session state and injects a hint into the prompt so the LLM
// picks different products this time.
func InjectPreviousProducts(ctx agent.CallbackContext, req *model.LLMRequest) (*model.LLMResponse, error) {
	prev, err := ctx.State().Get(stateKeyPreviousProducts)
	if err != nil {
		// No previous state — first run, proceed normally.
		return nil, nil
	}
	prevStr, ok := prev.(string)
	if !ok || prevStr == "" {
		return nil, nil
	}

	slog.Info("Injecting previously used products into prompt", "products", prevStr)

	// Append a hint to the last user content so the LLM sees it.
	for i := len(req.Contents) - 1; i >= 0; i-- {
		if req.Contents[i].Role == "user" {
			req.Contents[i].Parts = append(req.Contents[i].Parts,
				genai.NewPartFromText(fmt.Sprintf(
					"IMPORTANT: You previously suggested these products: %s. You MUST pick DIFFERENT complementary products this time to give the user fresh, new outfit ideas. Do NOT reuse any of those product IDs.",
					prevStr)))
			break
		}
	}
	return nil, nil
}

// SaveSelectedProducts is an AfterModelCallback that parses the LLM's final
// JSON response, extracts the product IDs from all outfits, and saves them
// to session state so the next invocation can avoid them.
func SaveSelectedProducts(ctx agent.CallbackContext, resp *model.LLMResponse, respErr error) (*model.LLMResponse, error) {
	if resp == nil || resp.Content == nil {
		return nil, nil
	}
	for _, part := range resp.Content.Parts {
		if part.Text == "" {
			continue
		}
		ids := extractProductIDs(part.Text)
		if len(ids) > 0 {
			data, _ := json.Marshal(ids)
			slog.Info("Saving selected products to session state", "products", string(data))
			if err := ctx.State().Set(stateKeyPreviousProducts, string(data)); err != nil {
				slog.Warn("Failed to save previously used products to state", "err", err)
			}
		}
	}
	return nil, nil
}

// extractProductIDs parses a JSON string containing outfits and returns all
// product IDs found. It handles both raw JSON and markdown-fenced JSON.
func extractProductIDs(text string) []string {
	var parsed OutfitResponse
	if err := json.Unmarshal([]byte(text), &parsed); err != nil {
		slog.Warn("Failed to parse product IDs from response", "err", err)
		return nil
	}

	var ids []string
	for _, outfit := range parsed.Outfits {
		for _, p := range outfit.Products {
			if p.ID != "" && !slices.Contains(ids, p.ID) {
				ids = append(ids, p.ID)
			}
		}
	}
	return ids
}

// NewStylistAgent creates an agent that acts as a fashion stylist,
// using the catalog agent as a tool to find items for the user.
func NewStylistAgent(project string, catalogAgent agent.Agent) (agent.Agent, error) {
	ctx := context.Background()
	// Don't pass a custom HTTPClient — the genai SDK needs to wrap its own
	// OAuth transport around the client when using ADC. Passing one we made
	// ourselves bypasses that wrapping and produces 401 CREDENTIALS_MISSING.
	m, err := gemini.NewModel(ctx, "gemini-3.1-pro-preview", &genai.ClientConfig{
		Backend:  genai.BackendVertexAI,
		Project:  project,
		Location: "global",
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create model: %w", err)
	}

	fittingTool, err := fittingroom.NewFittingTool()
	if err != nil {
		return nil, fmt.Errorf("failed to create fitting tool: %w", err)
	}

	imgtool, err := tools.NewImageTool()
	if err != nil {
		return nil, fmt.Errorf("failed to create image tool: %w", err)
	}

	stylingAgent, err := llmagent.New(llmagent.Config{
		Name:        "stylist",
		Model:       m,
		Description: "A fashion stylist that suggests items based on user preferences",
		Instruction: instructions,
		SubAgents:   []agent.Agent{catalogAgent},
		Tools: []tool.Tool{
			agenttool.New(catalogAgent, nil),
			fittingTool,
			imgtool,
			loadartifactstool.New(),
		},
		BeforeAgentCallbacks: []agent.BeforeAgentCallback{
			fittingroom.SaveIncomingBlobs,
			LockUserImageArtifact, // pin the original photo's artifact name to state for identity continuity
			tools.LogAgentInputCallback,
		},
		BeforeModelCallbacks: []llmagent.BeforeModelCallback{
			ExtractAndInjectUserImage,
			InjectPreviousProducts,
		},
		AfterModelCallbacks: []llmagent.AfterModelCallback{
			SaveSelectedProducts,
		},
		GenerateContentConfig: &genai.GenerateContentConfig{
			ResponseJsonSchema: adkStyleSchema(),
			ResponseMIMEType:   "application/json",
			ThinkingConfig: &genai.ThinkingConfig{
				IncludeThoughts: false,
			},
		},
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create stylist agent: %w", err)
	}

	return stylingAgent, nil
}

// data types for response.
type Product struct {
	ID       string
	Title    string
	Subtitle string
	Price    float32
	image    string
}
type Outfit struct {
	Image      string
	Commentary string
	Products   []Product
}
type OutfitResponse struct {
	Outfits []Outfit `json:"outfit"`
}

// adkStyleSchema returns the messy map[string]any form of the json schema.
// This syntax is awkward, but it works.
func adkStyleSchema() map[string]any {
	return map[string]any{
		"type": "object",
		"properties": map[string]any{
			"outfits": map[string]any{
				"type":     "array",
				"minItems": 3,
				"items": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"image": map[string]any{
							"type":        "string",
							"description": "artifact name of a generated fitting image, as generated by the fitting tool.",
						},
						"commentary": map[string]any{
							"type": "string",
						},
						"products": map[string]any{
							"type":     "array",
							"minItems": 2,
							"maxItems": 5,
							"items": map[string]any{
								"type": "object",
								"properties": map[string]any{
									"title": map[string]any{
										"type": "string",
									},
									"subtitle": map[string]any{
										"type": "string",
									},
									"price": map[string]any{
										"type": "number",
									},
									"id": map[string]any{
										"type": "string",
									},
								},
							},
						},
					},
				},
			},
		},
	}

}
