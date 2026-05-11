package tools

import (
	"log"

	"google.golang.org/adk/agent"
	"google.golang.org/genai"
)

func LogAgentInputCallback(ctx agent.CallbackContext) (*genai.Content, error) {
	for _, p := range ctx.UserContent().Parts {
		if len(p.Text) > 0 {
			log.Print(p.Text)
		} else {
			log.Printf("Unloggable User Input: %+v", p)
		}
	}
	return nil, nil
}
