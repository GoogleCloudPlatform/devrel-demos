// Package server implements the main MCP server logic.
package server

import (
	"context"
	"log"
	"net/http"
	"time"

	"github.com/danicat/godoctor/internal/config"
	"github.com/danicat/godoctor/internal/prompts"
	"github.com/danicat/godoctor/internal/resources/godoc"
	"github.com/danicat/godoctor/internal/tools/codereview"
	"github.com/danicat/godoctor/internal/tools/edit_code"
	"github.com/danicat/godoctor/internal/tools/getdocs"
	"github.com/danicat/godoctor/internal/tools/inspect"
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
	}, nil)

	return &Server{
		mcpServer: s,
		cfg:       cfg,
	}
}

// RegisterHandlers registers all available tools and prompts with the server.
func (s *Server) RegisterHandlers() {
	// Register tools
	getdocs.Register(s.mcpServer)
	codereview.Register(s.mcpServer, s.cfg.DefaultModel)
	if s.cfg.Experimental {
		inspect.Register(s.mcpServer)
		edit_code.Register(s.mcpServer)
	}

	// Register resources
	godoc.Register(s.mcpServer)

	// Register prompts
	s.mcpServer.AddPrompt(prompts.ImportThis("doc"), prompts.ImportThisHandler)
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
