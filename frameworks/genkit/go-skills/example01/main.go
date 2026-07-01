package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"github.com/firebase/genkit/go/plugins/middleware"
	"google.golang.org/genai"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: recipe <food|ingredient>")
		os.Exit(1)
	}

	input := os.Args[1]

	ctx := context.Background()

	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}, &middleware.Middleware{}))

	recipeFlow := genkit.DefineFlow(g, "recipeFlow", func(ctx context.Context, input string) (string, error) {
		prompt := fmt.Sprintf("Provide a recipe using %s", input)

		return genkit.GenerateText(ctx, g,
			ai.WithModel(googlegenai.ModelRef("googleai/gemini-flash-latest", &genai.GenerateContentConfig{
				ThinkingConfig: &genai.ThinkingConfig{
					ThinkingLevel: genai.ThinkingLevelLow,
				},
			})),
			ai.WithSystem(
				"You are a professional chef assistant with wide knowledge about recipes. "+
					"The user will give you a food or ingredient and you need to respond with a recipe. "+
					"Use specialised knowledge (skills) whenever possible. "+
					"Respond with ASCII formatting optimised for terminal output (no markdown).",
			),
			ai.WithPrompt(prompt),
			ai.WithUse(&middleware.Skills{SkillPaths: []string{"./skills"}}),
		)
	})

	result, err := recipeFlow.Run(ctx, input)
	if err != nil {
		log.Fatalf("Error running flow: %v", err)
	}

	fmt.Println(result)
}
