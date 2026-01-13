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
	"github.com/danicat/godoctor/internal/tools/describe"
	"github.com/danicat/godoctor/internal/tools/edit"
	"github.com/danicat/godoctor/internal/tools/edit_code"
	"github.com/danicat/godoctor/internal/tools/open"
	"github.com/danicat/godoctor/internal/tools/read_code"
	"github.com/danicat/godoctor/internal/tools/read_docs"
	"github.com/danicat/godoctor/internal/tools/review_code"
	"github.com/danicat/godoctor/internal/tools/write"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Server encapsulates the MCP server and its configuration.
type Server struct {
	mcpServer *mcp.Server
	cfg       *config.Config
}

// New creates a new Server instance.
func New(cfg *config.Config, version string) *Server {
	s := mcp.NewServer(&mcp.Implementation{
		Name:    "godoctor",
		Version: version,
	}, &mcp.ServerOptions{
		Instructions: instructions.Get(cfg.Experimental),
	})

	return &Server{
		mcpServer: s,
		cfg:       cfg,
	}
}

// RegisterHandlers registers all available tools and prompts with the server.
func (s *Server) RegisterHandlers() error {
	type toolDef struct {
		name         string
		experimental bool
		register     func(*mcp.Server)
	}

	availableTools := []toolDef{
		{name: "read_docs", experimental: false, register: read_docs.Register},
		{name: "review_code", experimental: false, register: func(srv *mcp.Server) {
			review_code.Register(srv, s.cfg.DefaultModel)
		}},
		{name: "edit_code", experimental: false, register: edit_code.Register},
		{name: "read_code", experimental: false, register: read_code.Register},
		{name: "open", experimental: true, register: open.Register},
		{name: "describe", experimental: true, register: describe.Register},
		{name: "edit", experimental: true, register: edit.Register},
		{name: "write", experimental: true, register: write.Register},
	}

	// Validate disabled tools
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
		if s.cfg.DisabledTools[t.name] {
			continue
		}
		if t.experimental && !s.cfg.Experimental {
			continue
		}
		t.register(s.mcpServer)
	}

	if s.cfg.Experimental {
		// Initialize the Knowledge Graph for the current project
		graph.Global.Initialize(".")

		code.Register(s.mcpServer)
		symbol.Register(s.mcpServer)
		project.Register(s.mcpServer)
	}

	// Register resources
	godoc.Register(s.mcpServer)

	// Register prompts
	s.mcpServer.AddPrompt(prompts.ImportThis("doc"), prompts.ImportThisHandler)

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
