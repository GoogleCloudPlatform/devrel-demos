// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package prompts

import (
	"context"
	"errors"
	"fmt"
	"os"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const localizePrompt = `
You are a localization specialist. Your task is to translate an article into a target language while strictly adhering to our localization guidelines.

You must follow these rules:

**1. Do Not Translate Technical Terms:**
   - All technical computer science and software engineering terms must remain in English. This is not an exhaustive list; use your best judgment for similar jargon.
   - Examples: ` + "`API`" + `, ` + "`backend`" + `, ` + "`CLI`" + `, ` + "`commit`" + `, ` + "`database`" + `, ` + "`frontend`" + `, ` + "`JSON`" + `, ` + "`LLM`" + `, ` + "`prompt`" + `, ` + "`pull request`" + `, ` + "`repository`" + `, ` + "`SDK`" + `, ` + "`server`" + `, ` + "`SSH`" + `.

**2. Do Not Translate Product & Brand Names:**
   - All product, company, and brand names must remain in their original form.
   - Examples: ` + "`Claude`" + `, ` + "`Gemini CLI`" + `, ` + "`Go`" + `, ` + "`GoDoctor`" + `, ` + "`Google Cloud`" + `, ` + "`Jules`" + `, ` + "`osquery`" + `.

**3. Maintain Formatting:**
   - Preserve all markdown formatting, including headings, lists, bold/italic text, and links.
   - Do not translate content within code blocks (` + "```" + `). Comments within code may be translated.
   - Keep all URLs and links unchanged.

**4. Tone and Style:**
   - Review existing articles in the target language to match the established professional yet approachable tone.
`

func Localize() *mcp.Prompt {
	return &mcp.Prompt{
		Name:        "localize",
		Description: "Translates the article currently being worked on into a target language.",
		Arguments: []*mcp.PromptArgument{
			{
				Name:        "target_language",
				Description: "The language to translate the article into.",
				Required:    true,
			},
		},
	}
}

func NewLocalizeHandler(guidelinePath string) mcp.PromptHandler {
	return func(ctx context.Context, req *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
		targetLanguage, ok := req.Params.Arguments["target_language"]
		if !ok {
			return nil, fmt.Errorf("target_language argument not provided")
		}

		guidelines := localizePrompt
		customGuidelines, err := os.ReadFile(guidelinePath)
		if err != nil {
			if !errors.Is(err, os.ErrNotExist) {
				return nil, err
			}
		} else {
			guidelines = string(customGuidelines)
		}

		prompt := fmt.Sprintf("Translate the work-in-progress article currently in your context into %s. You must follow the localization guidelines provided.", targetLanguage)

		return &mcp.GetPromptResult{
			Messages: []*mcp.PromptMessage{
				{
					Role: "user",
					Content: &mcp.TextContent{
						Text: guidelines + "\n\n" + prompt,
					},
				},
			},
		}, nil
	}
}
