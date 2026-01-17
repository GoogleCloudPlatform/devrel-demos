// Package main implements a simple photo restoration flow using Genkit.
package main

import (
	"context"
	"encoding/base64"
	"fmt"
	"io"
	"log"
	"mime"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	ctx := context.Background()

	// The API key.
	apiKey := os.Getenv("GEMINI_API_KEY")
	if apiKey == "" {
		log.Fatal("GEMINI_API_KEY environment variable must be set")
	}

	g := genkit.Init(ctx,
		genkit.WithPlugins(
			&googlegenai.GoogleAI{
				APIKey: apiKey,
			},
		),
	)

	// Define the model.
	nanobanana := genkit.LookupModel(g, "googleai/gemini-3-pro-image-preview")
	if nanobanana == nil {
		log.Fatal("model not found")
	}

	// Define the restoration prompt.
	const restorationPrompt = `
		You are an expert in photo restoration.
		Your task is to restore the following image to modern standards.
		The restored image should not contain any elements that were not present in the original image.
		The focus of the improvements should be on quality alone.
	`

	// Define the restore flow.
	restoreFlow := genkit.DefineFlow(g, "restore", func(ctx context.Context, imagePath string) (string, error) {
		// Read the image file.
		img, err := newPartFromFile(imagePath)
		if err != nil {
			return "", fmt.Errorf("failed to read image file: %v", err)
		}

		// Create the prompt parts.
		parts := []*ai.Part{
			ai.NewTextPart(restorationPrompt),
			img,
		}

		// Generate the restored image.
		resp, err := nanobanana.Generate(ctx,
			&ai.ModelRequest{
				Messages: []*ai.Message{
					{Content: parts},
				},
			},
			nil,
		)
		if err != nil {
			return "", fmt.Errorf("failed to generate restored image: %v", err)
		}

		// Get the restored image from the response.
		restoredImage := resp.Message.Content[0]

		// Save the restored image to a file.
		restoredImagePath := strings.Replace(imagePath, ".jpeg", "_restored.jpeg", 1)
		if err := os.WriteFile(restoredImagePath, []byte(restoredImage.Text), 0600); err != nil {
			return "", fmt.Errorf("failed to save restored image: %v", err)
		}

		return restoredImagePath, nil
	})

	// Define the evaluation prompt.
	const evaluationPrompt = `
		You are an expert in photo restoration.
		Your task is to evaluate the quality of a restored image compared to the original.
		Respond with "<<PASS>>" if the restored image is a significant improvement in quality over the original, and "<<FAIL>>" otherwise.
	`

	// Define the custom evaluator.
	genkit.DefineEvaluator(g, "custom/restoreEvaluator", nil, func(ctx context.Context, req *ai.EvaluatorCallbackRequest) (*ai.EvaluatorCallbackResponse, error) {
		// Get the original and restored images from the test case.
		originalImagePath, ok := req.Input.Input.(string)
		if !ok {
			return nil, fmt.Errorf("invalid input type: %T", req.Input.Input)
		}
		restoredImagePath, ok := req.Input.Output.(string)
		if !ok {
			return nil, fmt.Errorf("invalid output type: %T", req.Input.Output)
		}

		// Read the original and restored image files.
		originalImage, err := newPartFromFile(originalImagePath)
		if err != nil {
			return nil, fmt.Errorf("failed to read original image file: %v", err)
		}
		restoredImage, err := newPartFromFile(restoredImagePath)
		if err != nil {
			return nil, fmt.Errorf("failed to read restored image file: %v", err)
		}

		// Create the prompt parts.
		parts := []*ai.Part{
			ai.NewTextPart(evaluationPrompt),
			originalImage,
			restoredImage,
		}

		// Evaluate the restored image.
		resp, err := nanobanana.Generate(ctx,
			&ai.ModelRequest{
				Messages: []*ai.Message{
					{Content: parts},
				},
			},
			nil,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to evaluate restored image: %v", err)
		}

		// Get the evaluation result from the response.
		evaluationResult := resp.Message.Content[0].Text

		// Create the score.
		score := &ai.Score{
			Score:  evaluationResult == "<<PASS>>",
			Status: "PASS",
		}
		if evaluationResult != "<<PASS>>" {
			score.Status = "FAIL"
		}

		return &ai.EvaluatorCallbackResponse{
			Evaluation: []ai.Score{*score},
		}, nil
	})

	// Run the flow if a command-line argument is provided.
	if len(os.Args) > 1 {
		flowName := os.Args[1]
		if flowName == "restore" {
			imagePath := os.Args[2]
			_, err := restoreFlow.Run(context.Background(), imagePath)
			if err != nil {
				log.Fatalf("failed to run restore flow: %v", err)
			}
		}
	}
}

// newPartFromFile creates a new ai.Part from a file path.
// #nosec G304
func newPartFromFile(path string) (*ai.Part, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer func() {
		if err := f.Close(); err != nil {
			log.Printf("failed to close file: %v", err)
		}
	}()
	data, err := io.ReadAll(f)
	if err != nil {
		return nil, err
	}
	contentType := mime.TypeByExtension(filepath.Ext(path))
	if contentType == "" {
		contentType = http.DetectContentType(data)
	}
	return ai.NewMediaPart(contentType, base64.StdEncoding.EncodeToString(data)), nil
}
