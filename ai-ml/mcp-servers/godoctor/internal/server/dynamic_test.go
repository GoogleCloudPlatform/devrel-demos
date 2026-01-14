package server_test

import (
	"testing"

	"github.com/danicat/godoctor/internal/config"
	"github.com/danicat/godoctor/internal/server"
)

// TestDynamicProfile verifies that the Dynamic profile starts with only the master tool.
// We can't easily test the registeredTools map since it's private, but we can verify IsToolEnabled
// and build the server.
func TestDynamicProfile(t *testing.T) {
	cfg := &config.Config{
		Profile:       config.ProfileDynamic,
		AllowedTools:  make(map[string]bool),
		DisabledTools: make(map[string]bool),
	}

	// 1. Verify Config Logic
	if !cfg.IsToolEnabled("ask_the_master_gopher", true) {
		t.Error("ask_the_master_gopher should be enabled in Dynamic profile")
	}
	if cfg.IsToolEnabled("smart_edit", false) {
		t.Error("smart_edit should be disabled in Dynamic profile initially")
	}

	// 2. Verify Server Init
	srv := server.New(cfg, "v0.8.0")
	// Since registeredTools is private, we can't inspect it directly here without reflection or exposing it.
	// But RegisterHandlers should run without error.
	if err := srv.RegisterHandlers(); err != nil {
		t.Errorf("RegisterHandlers failed for Dynamic profile: %v", err)
	}

	// Note: Functional verification of UpdateTools requires running the master_gopher handler which asks LLM.
	// That is covered by manual verification or mocking the updater in unit tests.
}
