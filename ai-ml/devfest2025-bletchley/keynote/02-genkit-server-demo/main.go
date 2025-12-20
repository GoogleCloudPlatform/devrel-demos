package main

import (
	"context"
	"flag"
	"log"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"google.golang.org/genai"
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

	// Define a simple flow that takes a string input.
	genkit.DefineFlow(g, "helloFlow", func(ctx context.Context, input string) (string, error) {
		resp, err := genkit.Generate(ctx, g,
			ai.WithModelName(*model),
			ai.WithPrompt(input),
			ai.WithConfig(&genai.GenerateContentConfig{
				Temperature: genai.Ptr[float32](1.0),
			}),
		)
		if err != nil {
			return "", err
		}

		return resp.Text(), nil
	})

	// Keep the process running to serve the flow.
	log.Println("Genkit flow server running...")
	<-ctx.Done()
}
