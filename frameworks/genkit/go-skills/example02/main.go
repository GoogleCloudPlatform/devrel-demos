package main

import (
	"context"
	"encoding/base64"
	"fmt"
	"log"
	"log/slog"
	"os"
	"path/filepath"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"github.com/firebase/genkit/go/plugins/middleware"
	"google.golang.org/genai"
)

// Input defines the schema for the Renaissance flow, accepting a Base64 image data URI.
type Input struct {
	URL string `json:"url"`
}

// Output defines the schema for the flow output, containing both text explanation and image data.
type Output struct {
	Text  string `json:"text"`
	Image string `json:"image"` // Base64 image data URI
}

func main() {
	// Configure logging to suppress verbose Genkit trace and info logs on standard output.
	logger := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
		Level: slog.LevelError,
	}))
	slog.SetDefault(logger)

	if len(os.Args) < 2 {
		log.Fatalf("Usage: go run . <path-to-image>")
	}
	filePath := os.Args[1]

	// Read and convert the image to a Base64 Data URI.
	data, err := os.ReadFile(filePath)
	if err != nil {
		log.Fatalf("Failed to read file: %v", err)
	}
	dataURI := "data:image/jpeg;base64," + base64.StdEncoding.EncodeToString(data)

	ctx := context.Background()

	// 1. Initialize Genkit with standard Google AI and Middleware plugins.
	g := genkit.Init(ctx, genkit.WithPlugins(
		&googlegenai.GoogleAI{},
		&middleware.Middleware{},
	))

	// 2. Define a Genkit Flow for actual image-to-image restoration.
	renaissanceFlow := genkit.DefineFlow(g, "renaissanceFlow", func(ctx context.Context, input Input) (Output, error) {
		// 3. Prompt the model with multimodal input and configure it to output both TEXT and IMAGE modalities.
		resp, err := genkit.Generate(ctx, g,
			ai.WithModel(googlegenai.ModelRef("googleai/gemini-3.1-flash-image", &genai.GenerateContentConfig{
				ResponseModalities: []string{"TEXT", "IMAGE"},
			})),
			ai.WithSystem("You are Renaissance, a multimodal art restoration AI. First, analyze the image to determine "+
				"the type of image, then invoke the corresponding restoration skills as approriate. "+
				"Finally, perform a highly precise restoration and output the restored IMAGE. "+
				"REQUIRED: In your response, return a text part summarising your process and "+
				"naming any skills used. ",
			),
			ai.WithMessages(
				ai.NewUserMessage(
					ai.NewTextPart("Please restore this image using the appropriate techniques."),
					ai.NewMediaPart("image/jpeg", input.URL),
				),
			),
			// Load agent skills dynamically from the "./skills" directory.
			ai.WithUse(&middleware.Skills{SkillPaths: []string{"./skills"}}),
		)
		if err != nil {
			return Output{}, err
		}

		// Return both the explanation and the generated media content (image data URI).
		return Output{
			Text:  resp.Text(),
			Image: resp.Media(),
		}, nil
	})

	// 4. Run the flow with the prepared input.
	fmt.Println("Running renaissanceFlow...")
	result, err := renaissanceFlow.Run(ctx, Input{URL: dataURI})
	if err != nil {
		log.Fatalf("Flow execution failed: %v", err)
	}

	// 5. Render the textual restoration plan if it is actual text and not the raw image data.
	if result.Text != "" && !strings.HasPrefix(result.Text, "data:") {
		fmt.Printf("\nRestoration Plan:\n%s\n", result.Text)
	} else {
		fmt.Println("\nRestoration process completed (no separate textual explanation returned).")
	}

	// 6. Parse, decode, and save the output image locally.
	if !strings.HasPrefix(result.Image, "data:") {
		log.Fatalf("Unsupported or invalid image format returned by the flow")
	}

	parts := strings.Split(result.Image, ";base64,")
	if len(parts) != 2 {
		log.Fatalf("Invalid data URI format received from flow")
	}

	decodedImage, err := base64.StdEncoding.DecodeString(parts[1])
	if err != nil {
		log.Fatalf("Failed to decode restored image base64 data: %v", err)
	}

	ext := filepath.Ext(filePath)
	base := filePath[:len(filePath)-len(ext)]
	outputPath := base + "_restored.png"

	err = os.WriteFile(outputPath, decodedImage, 0644)
	if err != nil {
		log.Fatalf("Failed to write output image file: %v", err)
	}

	// 7. Print the completion confirmation.
	fmt.Printf("\nSuccessfully saved restored image to %s\n", outputPath)
}
