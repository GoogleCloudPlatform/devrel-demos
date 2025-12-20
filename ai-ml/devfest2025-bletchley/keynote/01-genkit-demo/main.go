package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	ctx := context.Background()

	// Check for Google Cloud Project
	if os.Getenv("GOOGLE_CLOUD_PROJECT") == "" {
		log.Fatal("Error: GOOGLE_CLOUD_PROJECT is not set. Please set it to your Google Cloud Project ID.")
	}

	location := os.Getenv("GOOGLE_CLOUD_LOCATION")
	if location == "" {
		location = "us-central1"
	}

	model := flag.String("model", "vertexai/gemini-2.5-flash", "model name")
	flag.Parse()

	// Initialize Genkit with the Google AI plugin.
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.VertexAI{Location: location}))

	// Define a simple Genkit flow.
	helloFlow := genkit.DefineFlow(
		g,
		"helloFlow",
		func(ctx context.Context, prompt string) (string, error) {
			resp, err := genkit.Generate(ctx, g, ai.WithModelName(*model), ai.WithPrompt(prompt))
			if err != nil {
				return "", err
			}
			return resp.Text(), nil
		},
	)

	// Invoke the flow
	prompt := "Say something nice about Bletchley Park"
	result, err := helloFlow.Run(ctx, prompt)
	if err != nil {
		log.Fatalf("Flow invocation failed: %v", err)
	}

	fmt.Printf("Response: %s\n", result)
}
