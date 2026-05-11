package rootagent

import (
	"context"
	"fmt"

	"google.golang.org/adk/agent"
	"google.golang.org/adk/agent/llmagent"
	"google.golang.org/adk/model/gemini"
	"google.golang.org/genai"
)

func NewRootAgent(project string, fittingAgent agent.Agent, catalogAgent agent.Agent, stylistAgent agent.Agent) (agent.Agent, error) {
	ctx := context.Background()
	// Using a fast model for the router/root agent
	m, err := gemini.NewModel(ctx, "gemini-3-flash-preview", &genai.ClientConfig{
		Backend:  genai.BackendVertexAI,
		Project:  project,
		Location: "global",
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create model: %w", err)
	}

	return llmagent.New(llmagent.Config{
		Name:        "root_agent",
		Model:       m,
		Description: "A root agent that delegates to other agents",
		Instruction: "You are a helpful shoping assistant. If the user asks about fitting items or generating images with items, delegate to the fitting room agent. If the user asks about products, prices, or availability, delegate to the catalog agent. If the user asks for styling advice or outfit curation, delegate to the stylist agent.",
		SubAgents:   []agent.Agent{fittingAgent, catalogAgent, stylistAgent},
	})
}
