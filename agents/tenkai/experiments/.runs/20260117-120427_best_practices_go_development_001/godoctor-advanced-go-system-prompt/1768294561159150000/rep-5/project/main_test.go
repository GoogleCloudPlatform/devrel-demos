package main

import (
	"context"
	"os"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/stretchr/testify/require"
)

func TestRestoreFlow(t *testing.T) {
	ctx := context.Background()

	g := genkit.Init(ctx)

	// Create a dummy elvira.jpeg file.
	err := os.WriteFile("elvira.jpeg", []byte("elvira"), 0600)
	require.NoError(t, err)

	// Define a fake model.
	genkit.DefineModel(g, "googleai/gemini-3-pro-image-preview", nil, func(_ context.Context, _ *ai.ModelRequest, _ ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		return &ai.ModelResponse{
			Message: &ai.Message{
				Content: []*ai.Part{
					ai.NewTextPart("restored image"),
				},
			},
		}, nil
	})

	// Define the restore flow.
	restoreFlow := genkit.DefineFlow(g, "restore", func(_ context.Context, _ string) (string, error) {
		// Create a dummy elvira_restored.jpeg file.
		err := os.WriteFile("elvira_restored.jpeg", []byte("restored elvira"), 0600)
		require.NoError(t, err)
		return "elvira_restored.jpeg", nil
	})

	// Run the restore flow.
	_, err = restoreFlow.Run(ctx, "elvira.jpeg")
	require.NoError(t, err)

	// Check if the restored image was created.
	_, err = os.Stat("elvira_restored.jpeg")
	require.NoError(t, err)

	// Clean up the images.
	err = os.Remove("elvira.jpeg")
	require.NoError(t, err)
	err = os.Remove("elvira_restored.jpeg")
	require.NoError(t, err)
}

func TestRestoreEvaluator(t *testing.T) {
	ctx := context.Background()

	g := genkit.Init(ctx)

	// Create dummy image files.
	err := os.WriteFile("elvira.jpeg", []byte("elvira"), 0600)
	require.NoError(t, err)
	err = os.WriteFile("elvira_restored.jpeg", []byte("restored elvira"), 0600)
	require.NoError(t, err)

	// Define a fake model.
	genkit.DefineModel(g, "googleai/gemini-3-pro-image-preview", nil, func(_ context.Context, _ *ai.ModelRequest, _ ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		return &ai.ModelResponse{
			Message: &ai.Message{
				Content: []*ai.Part{
					ai.NewTextPart("<<PASS>>"),
				},
			},
		}, nil
	})

	// Define the custom evaluator.
	genkit.DefineEvaluator(g, "custom/restoreEvaluator", nil, func(_ context.Context, _ *ai.EvaluatorCallbackRequest) (*ai.EvaluatorCallbackResponse, error) {
		return &ai.EvaluatorCallbackResponse{
			Evaluation: []ai.Score{
				{
					Score:  true,
					Status: "PASS",
				},
			},
		}, nil
	})

	// Run the evaluator.
	evaluator := genkit.LookupEvaluator(g, "custom/restoreEvaluator")
	require.NotNil(t, evaluator)

	resp, err := evaluator.Evaluate(ctx, &ai.EvaluatorRequest{
		Dataset: []*ai.Example{
			{
				Input:  "elvira.jpeg",
				Output: "elvira_restored.jpeg",
			},
		},
	})
	require.NoError(t, err)
	require.Len(t, *resp, 1)
	require.Len(t, (*resp)[0].Evaluation, 1)
	require.True(t, (*resp)[0].Evaluation[0].Score.(bool))

	// Clean up the images.
	err = os.Remove("elvira.jpeg")
	require.NoError(t, err)
	err = os.Remove("elvira_restored.jpeg")
	require.NoError(t, err)
}
