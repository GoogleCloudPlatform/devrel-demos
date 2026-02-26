package main

import (
	"context"
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
		genkit.WithDefaultModel("vertexai/gemini-2.5-flash"),
	)

	// Define the greeter flow
	genkit.DefineFlow(g, "greeter", func(ctx context.Context, name *string) (string, error) {
		prompt := genkit.LookupPrompt(g, "greeter")

		input := map[string]any{
			"name": name,
		}

		resp, err := prompt.Execute(ctx, ai.WithInput(input))
		if err != nil {
			return "", err
		}
		return resp.Text(), nil
	})

	<-ctx.Done()
}
