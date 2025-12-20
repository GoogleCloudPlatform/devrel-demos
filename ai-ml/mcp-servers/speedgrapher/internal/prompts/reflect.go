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

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const reflectionPrompt = `**Objective: Session Reflection and Process Improvement**

Your goal is to analyze the complete transcript of the current interactive session to identify key learnings and propose concrete improvements for future collaboration. This is a self-improvement exercise to make our pairing sessions more efficient, accurate, and effective.

**Instructions:**

Please review the session from the beginning and focus on the following areas:

1.  **Efficiency and Workflow:**
    *   Identify any instances of repeated errors (e.g., multiple build failures for the same underlying reason).
    *   Pinpoint moments where a different approach or a better initial understanding could have saved steps or time.
    *   Were there any detours or dead-ends that could have been avoided?

2.  **Technical Accuracy:**
    *   Recall any incorrect assumptions made about APIs, SDKs, or project conventions.
    *   Note any logical errors in the code that required correction.
    *   Highlight instances where user feedback was essential to correct a technical misunderstanding.

3.  **Collaboration and Communication:**
    *   Assess the clarity and effectiveness of your communication.
    *   Did you correctly interpret the user's intent at all times? Were there misunderstandings?
    *   Evaluate your tone. Was it consistently helpful, objective, and collaborative?
    *   Did you ask for clarification when a request was ambiguous, or did you make assumptions?

**Output Format:**

Please structure your reflection in the following format:

**Key Learnings from this Session:**

*   **Learning 1: [A concise, one-sentence summary of the learning.]**
    *   **Observation:** [Describe the specific event or pattern from the session that led to this learning. Provide examples.]
    *   **Future Action:** [Propose a concrete, actionable step you will take in the future to apply this learning and improve your process.]

*   **Learning 2: [Another concise summary.]**
    *   **Observation:** [Description and examples.]
    *   **Future Action:** [Proposed improvement.]

*(Continue for all major learnings identified.)*`

func Reflect() *mcp.Prompt {
	return &mcp.Prompt{
		Name:        "reflect",
		Description: "Analyzes the current session and proposes improvements to the development process.",
	}
}

func ReflectHandler(ctx context.Context, req *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
	return &mcp.GetPromptResult{
		Messages: []*mcp.PromptMessage{
			{
				Role: "assistant",
				Content: &mcp.TextContent{
					Text: reflectionPrompt,
				},
			},
		},
	}, nil
}
