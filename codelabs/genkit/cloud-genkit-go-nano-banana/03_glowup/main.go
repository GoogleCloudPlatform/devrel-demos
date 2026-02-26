package main

import (
	"context"
	"encoding/base64"
	"errors"
	"flag"
	"fmt"
	"log"
	"mime"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	url := flag.String("url", "", "url of the image to restore")
	contentType := flag.String("contentType", "image/jpeg", "content type of the image (default: image/jpeg)")
	flag.Parse()

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	// Initialize Genkit with the Vertex AI plugin
	g := genkit.Init(ctx,
		genkit.WithPlugins(&googlegenai.VertexAI{}),
	)

	// Input schema for the glowUp flow
	type Input struct {
		URL         string `json:"url,omitempty"`
		ContentType string `json:"contentType,omitempty"`
	}

	glowup := genkit.DefineFlow(g, "glowUp", func(ctx context.Context, input Input) (string, error) {
		// 1. Retrieve prompt
		prompt := genkit.LookupPrompt(g, "glowup")
		if prompt == nil {
			return "", errors.New("prompt 'glowup' not found")
		}

		resp, err := prompt.Execute(ctx, ai.WithInput(input))
		if err != nil {
			return "", fmt.Errorf("generation failed: %w", err)
		}

		return resp.Media(), nil
	})

	// triggers the flow and returns the encoded response from the model
	out, err := glowup.Run(ctx, Input{URL: *url, ContentType: *contentType})
	if err != nil {
		log.Fatalln(err)
	}

	// decodes image data and returns the appropriate file extension
	data, ext, err := decode(out)
	if err != nil {
		log.Fatalln(err)
	}

	// writes restored file to disk
	filename := "restored" + ext
	if err := os.WriteFile(filename, data, 0644); err != nil {
		log.Fatalln(err)
	}
}

// decode returns the decoded data and the file extension appropriate for the mime type
func decode(text string) ([]byte, string, error) {
	if !strings.HasPrefix(text, "data:") {
		return nil, "", errors.New("unsupported enconding format")
	}
	text = strings.TrimPrefix(text, "data:")
	parts := strings.Split(text, ";base64,")

	mimeType := parts[0]
	decoded, err := base64.StdEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, "", err
	}

	ext, err := mime.ExtensionsByType(mimeType)
	if err != nil {
		return nil, "", err
	}

	return decoded, ext[0], nil
}
