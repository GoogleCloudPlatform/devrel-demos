package tools

import (
	"fmt"
	"os"

	"github.com/google/uuid"

	"google.golang.org/adk/tool"
	"google.golang.org/adk/tool/functiontool"
	"google.golang.org/genai"
)

func NewOutfitGenTool() (tool.Tool, error) {
	return functiontool.New(functiontool.Config{
		Name:        "generate_outfit_image",
		Description: "generates an image of a model wearing an outfit based on a text description, returns the artifact name of the generated image",
	}, generateOutfitImage)
}

type GenerateOutfitImageArgs struct {
	Prompt string `json:"prompt" jsonschema:"detailed description of the outfit to generate"`
}

type GenerateOutfitImageResult struct {
	ArtifactName string `json:"artifact_name" jsonschema:"the artifact name of the generated image"`
}

func generateOutfitImage(ctx tool.Context, args GenerateOutfitImageArgs) (GenerateOutfitImageResult, error) {
	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		Backend:  genai.BackendVertexAI,
		Project:  os.Getenv("GOOGLE_CLOUD_PROJECT"),
		Location: "global",
	})
	if err != nil {
		return GenerateOutfitImageResult{}, err
	}

	systemInstruction := "You are an expert fashion photographer. Generate a highly realistic, full-body portrait of a model wearing the described outfit in an appropriate setting."
	parts := []*genai.Part{
		genai.NewPartFromText(systemInstruction),
		genai.NewPartFromText(args.Prompt),
	}

	resp, err := client.Models.GenerateContent(ctx, "gemini-2.5-flash-image", []*genai.Content{genai.NewContentFromParts(parts, "user")}, &genai.GenerateContentConfig{
		ResponseModalities: []string{"TEXT", "IMAGE"},
		ImageConfig:        &genai.ImageConfig{AspectRatio: "9:16"},
	})
	if err != nil {
		return GenerateOutfitImageResult{}, err
	}

	if len(resp.Candidates) == 0 || resp.Candidates[0].Content == nil || len(resp.Candidates[0].Content.Parts) == 0 {
		return GenerateOutfitImageResult{}, fmt.Errorf("no content generated")
	}

	// Find the image part — response may contain both TEXT and IMAGE parts
	var genPart *genai.Part
	for _, p := range resp.Candidates[0].Content.Parts {
		if p.InlineData != nil {
			genPart = p
			break
		}
	}
	if genPart == nil {
		return GenerateOutfitImageResult{}, fmt.Errorf("no image generated")
	}

	artName := fmt.Sprintf("generated_outfit_%s_%s", ctx.InvocationID(), uuid.NewString()[:8])
	_, err = ctx.Artifacts().Save(ctx, artName, genPart)
	if err != nil {
		return GenerateOutfitImageResult{}, err
	}

	return GenerateOutfitImageResult{ArtifactName: artName}, nil
}
