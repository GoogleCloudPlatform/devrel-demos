package stylist

import (
	"context"
	"encoding/json"
	"iter"
	"os"
	"strings"
	"testing"

	"goagents/catalog"

	"google.golang.org/adk/agent"
	"google.golang.org/adk/artifact"
	"google.golang.org/adk/runner"
	"google.golang.org/adk/session"
	"google.golang.org/genai"
)

func TestNewStylistAgent_Creation(t *testing.T) {
	// Project for Vertex AI auth via ADC
	project := os.Getenv("GOOGLE_CLOUD_PROJECT")
	if project == "" {
		t.Skip("GOOGLE_CLOUD_PROJECT not set, skipping integration test that requires Gemini model initialization.")
	}

	// Create actual Catalog Agent
	catalogAgent, err := catalog.NewCatalogAgent(project, "../catalog/catalog.yaml")
	if err != nil {
		t.Fatalf("Failed to create actual catalog agent: %v", err)
	}

	var stylistAgent agent.Agent
	stylistAgent, err = NewStylistAgent(project, catalogAgent)
	if err != nil {
		t.Fatalf("NewStylistAgent failed: %v", err)
	}

	if stylistAgent == nil {
		t.Fatal("NewStylistAgent returned a nil agent")
	}

	if stylistAgent.Name() != "stylist" {
		t.Errorf("Expected agent name 'stylist', got '%s'", stylistAgent.Name())
	}
}

func TestStyleMe_Script(t *testing.T) {
	project := os.Getenv("GOOGLE_CLOUD_PROJECT")
	if project == "" {
		t.Skip("GOOGLE_CLOUD_PROJECT not set, skipping agent interaction scenarios.")
	}

	// Create actual Catalog Agent
	catalogAgent, err := catalog.NewCatalogAgent(project, "../catalog/catalog.yaml")
	if err != nil {
		t.Fatalf("Failed to create actual catalog agent for scenarios: %v", err)
	}

	var stylistAgent agent.Agent
	stylistAgent, err = NewStylistAgent(project, catalogAgent)
	if err != nil {
		t.Fatalf("Failed to create stylist agent for scenarios: %v", err)
	}

	// Create a new runner with the stylist agent and an in-memory session service.
	// For a more robust test, you might want to configure artifact and memory services too.
	ctx := context.Background()
	runnerConfig := runner.Config{
		AppName:         "stylist-test-app",
		Agent:           stylistAgent,
		SessionService:  session.InMemoryService(),
		ArtifactService: artifact.InMemoryService(),
	}
	r, err := runner.New(runnerConfig)
	if err != nil {
		t.Fatalf("Failed to create runner: %v", err)
	}

	sess, _ := runnerConfig.SessionService.Create(ctx, &session.CreateRequest{
		AppName: runnerConfig.AppName,
		UserID:  "test-user",
	})
	// TODO: Run our expected script here.
	// Send a user image, with a product.
	// go:embed testdata/userimage2.jpg
	var inlineUserPic []byte
	runnerConfig.ArtifactService.Save(ctx, &artifact.SaveRequest{
		AppName:   sess.Session.AppName(),
		UserID:    sess.Session.UserID(),
		SessionID: sess.Session.ID(),
		Part:      genai.NewPartFromBytes(inlineUserPic, "image/jpeg"),
		Version:   0,
	})
	step1 := genai.Content{
		Parts: []*genai.Part{
			genai.NewPartFromText("Location: Las Vegas"),
			genai.NewPartFromText("Occasion: Google Cloud Next"),
		},
		Role: genai.RoleUser,
	}
	// Then send a StyleRequest prompt
	resp := r.Run(
		ctx,
		sess.Session.UserID(),
		sess.Session.ID(),
		&step1,
		agent.RunConfig{})
	rtext, err := getTextResp(t, resp)
	// Ensure it parses properly
	var rout OutfitResponse
	if err := json.Unmarshal([]byte(rtext), &rout); err != nil {
		t.Errorf("failed to parse json response: %v", err)
		return
	}
}

func getTextResp(t *testing.T, resp iter.Seq2[*session.Event, error]) (string, error) {

	var rt strings.Builder
	for event, err := range resp {
		if err != nil {
			t.Logf("Err: %+v\n", err)
			continue
		}
		if event.Content.Parts != nil {
			for _, p := range event.Content.Parts {
				// t.Logf("Part: %+v\n", p)
				rt.WriteString(p.Text)
			}
		}
	}
	return rt.String(), nil
}
