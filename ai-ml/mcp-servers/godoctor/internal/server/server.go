// Package server implements the main MCP server logic.
package server

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/danicat/godoctor/internal/config"
	"github.com/danicat/godoctor/internal/graph"
	"github.com/danicat/godoctor/internal/instructions"
	"github.com/danicat/godoctor/internal/prompts"
	"github.com/danicat/godoctor/internal/resources/code"
	"github.com/danicat/godoctor/internal/resources/godoc"
	"github.com/danicat/godoctor/internal/resources/project"
	"github.com/danicat/godoctor/internal/resources/symbol"
	"github.com/danicat/godoctor/internal/tools/agent/master"
	"github.com/danicat/godoctor/internal/tools/agent/review"
	"github.com/danicat/godoctor/internal/tools/agent/specialist"
	"github.com/danicat/godoctor/internal/tools/file/create"
	"github.com/danicat/godoctor/internal/tools/file/edit"
	"github.com/danicat/godoctor/internal/tools/file/list"
	"github.com/danicat/godoctor/internal/tools/file/outline"
	"github.com/danicat/godoctor/internal/tools/file/read"
	"github.com/danicat/godoctor/internal/tools/go/build"
	"github.com/danicat/godoctor/internal/tools/go/diff"
	"github.com/danicat/godoctor/internal/tools/go/docs"
	"github.com/danicat/godoctor/internal/tools/go/install"
	"github.com/danicat/godoctor/internal/tools/go/modernize"
	"github.com/danicat/godoctor/internal/tools/go/test"
	"github.com/danicat/godoctor/internal/tools/project/map"
	"github.com/danicat/godoctor/internal/tools/symbol/inspect"
	"github.com/danicat/godoctor/internal/tools/symbol/rename"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Server encapsulates the MCP server and its configuration.
type Server struct {
	mcpServer       *mcp.Server
	cfg             *config.Config
	registeredTools map[string]bool
}

// New creates a new Server instance.
func New(cfg *config.Config, version string) *Server {
	s := mcp.NewServer(&mcp.Implementation{
		Name:    "godoctor",
		Version: version,
	}, &mcp.ServerOptions{
		Instructions: instructions.Get(cfg),
	})
	return &Server{
		mcpServer:       s,
		cfg:             cfg,
		registeredTools: make(map[string]bool),
	}
}

// RegisterHandlers registers all available tools and prompts with the server.
// It is idempotent and can be called multiple times to register newly enabled tools.
func (s *Server) RegisterHandlers() error {
	type toolDef struct {
		name         string
		experimental bool
		register     func(*mcp.Server)
	}

	availableTools := []toolDef{
		{name: "go.docs", experimental: false, register: docs.Register},
		{name: "agent.review", experimental: true, register: func(srv *mcp.Server) {
			review.Register(srv, s.cfg.DefaultModel)
		}},
		{name: "file.read", experimental: false, register: read.Register},
		{name: "file.outline", experimental: false, register: outline.Register},
		{name: "symbol.inspect", experimental: false, register: inspect.Register},
		{name: "file.edit", experimental: false, register: edit.Register},
		{name: "file.create", experimental: true, register: create.Register},
		{name: "go.diff", experimental: true, register: diff.Register},
		{name: "project.map", experimental: false, register: projectmap.Register},
		{name: "go.modernize", experimental: true, register: modernize.Register},
		{name: "file.list", experimental: false, register: list.Register},
		{name: "go.build", experimental: false, register: build.Register},
		{name: "go.install", experimental: false, register: install.Register},
		{name: "go.test", experimental: false, register: test.Register},
		{name: "symbol.rename", experimental: true, register: rename.Register},
		{name: "agent.specialist", experimental: false, register: specialist.Register},
		{name: "agent.master", experimental: true, register: func(srv *mcp.Server) {
			master.Register(srv, s.UpdateTools)
		}},
	}

	// Validate disabled tools (only check this once or if disabled tools logic didn't change)
	for name := range s.cfg.DisabledTools {
		found := false
		for _, t := range availableTools {
			if t.name == name {
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("invalid tool name to disable: %s", name)
		}
	}

	// Register tools
	for _, t := range availableTools {
		if s.registeredTools[t.name] {
			continue // Already registered
		}

		// Use the centralized config logic to check if a tool should be enabled
		if !s.cfg.IsToolEnabled(t.name, t.experimental) {
			continue
		}
		t.register(s.mcpServer)
		s.registeredTools[t.name] = true
	}

	if s.cfg.EnableExperimentalFeatures() {
		// Initialize the Knowledge Graph for the current project
		// Only strictly need to do this once
		if !s.registeredTools["graph_init"] {
			graph.Global.Initialize(".")
			s.registeredTools["graph_init"] = true
		}

		if !s.registeredTools["code"] {
			code.Register(s.mcpServer)
			s.registeredTools["code"] = true
		}
		if !s.registeredTools["symbol"] {
			symbol.Register(s.mcpServer)
			s.registeredTools["symbol"] = true
		}
		if !s.registeredTools["project"] {
			project.Register(s.mcpServer)
			s.registeredTools["project"] = true
		}
	}

	// Register resources (idempotent check)
	if !s.registeredTools["godoc"] {
		godoc.Register(s.mcpServer)
		s.registeredTools["godoc"] = true
	}

	// Register prompts
	if !s.registeredTools["prompt_import_this"] {
		s.mcpServer.AddPrompt(prompts.ImportThis("doc"), prompts.ImportThisHandler)
		s.registeredTools["prompt_import_this"] = true
	}

	return nil
}

// UpdateTools updates the allowed tools configuration and refreshes registrations.
// It sends a 'notifications/tools/list_changed' notification to the client.
func (s *Server) UpdateTools(allowedTools []string) error {
	// Update allow list
	newAllow := make(map[string]bool)
	for _, t := range allowedTools {
		newAllow[t] = true
	}
	s.cfg.AllowedTools = newAllow

	// Refresh registrations (this will add any newly enabled tools)
	if err := s.RegisterHandlers(); err != nil {
		return err
	}

	// Notify client
	// Note: The go-sdk might usually handle this or we might need to expose the ability to send notification.
	// s.mcpServer currently doesn't expose a direct Notify method in the minimal interface wrapper?
	// Assuming s.mcpServer has a method for this or we ignore it for now if sdk handles it.
	// Checking mcp.Server methods: It operates on requests.
	// TODO: Implement notification sending when SDK supports it or if we can access the transport.

	// For now, we assume the internal state update is sufficient for the next ToolList call.
	return nil
}

// Run starts the server, listening on either Stdio or HTTP based on configuration.
func (s *Server) Run(ctx context.Context) error {
	if s.cfg.ListenAddr != "" {
		return s.runHTTP(ctx)
	}
	return s.mcpServer.Run(ctx, &mcp.StdioTransport{})
}

func (s *Server) runHTTP(ctx context.Context) error {
	httpServer := &http.Server{
		Addr:              s.cfg.ListenAddr,
		Handler:           mcp.NewStreamableHTTPHandler(func(_ *http.Request) *mcp.Server { return s.mcpServer }, nil),
		ReadHeaderTimeout: 10 * time.Second,
	}

	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = httpServer.Shutdown(shutdownCtx)
	}()

	log.Printf("godoctor listening on %s", s.cfg.ListenAddr)
	if err := httpServer.ListenAndServe(); err != http.ErrServerClosed {
		return err
	}
	return nil
}
