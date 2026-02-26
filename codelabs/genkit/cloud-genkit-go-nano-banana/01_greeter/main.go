package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	// Initialize Genkit with the Vertex AI plugin
	g := genkit.Init(ctx,
		genkit.WithPlugins(&googlegenai.VertexAI{}),
	)

	// Define the greeter flow
	genkit.DefineFlow(g, "greeter", func(ctx context.Context, name string) (string, error) {
		text, err := genkit.GenerateText(ctx, g,
			ai.WithModelName("vertexai/gemini-2.5-pro"),
			ai.WithPrompt("Say a warm and creative hello to %s", name),
		)
		if err != nil {
			return "", err
		}

		return text, nil
	})

	// Register the flow here in the next steps
	log.Println("GlowUp initialized. Ready for flows.")
	<-ctx.Done()
}
