// Package server implements the main MCP server logic.
package server

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"strings"

	"github.com/danicat/godoctor/internal/config"
	"github.com/danicat/godoctor/internal/instructions"
	"github.com/danicat/godoctor/internal/prompts"
	"github.com/danicat/godoctor/internal/resources/code"
	resgodoc "github.com/danicat/godoctor/internal/resources/godoc"
	"github.com/danicat/godoctor/internal/resources/symbol"
	"github.com/danicat/godoctor/internal/roots"
	"github.com/modelcontextprotocol/go-sdk/mcp"

	// Tools
	"github.com/danicat/godoctor/internal/tools/agent/review"
	"github.com/danicat/godoctor/internal/tools/cmd/run"
	"github.com/danicat/godoctor/internal/tools/file/create"
	"github.com/danicat/godoctor/internal/tools/file/edit"
	"github.com/danicat/godoctor/internal/tools/file/list"
	"github.com/danicat/godoctor/internal/tools/file/outline"
	"github.com/danicat/godoctor/internal/tools/file/read"
	"github.com/danicat/godoctor/internal/tools/go/build"
	"github.com/danicat/godoctor/internal/tools/go/diff"
	"github.com/danicat/godoctor/internal/tools/go/docs"
	"github.com/danicat/godoctor/internal/tools/go/get"
	"github.com/danicat/godoctor/internal/tools/go/modernize"
	"github.com/danicat/godoctor/internal/tools/go/test"
	"github.com/danicat/godoctor/internal/tools/symbol/inspect"
	"github.com/danicat/godoctor/internal/tools/symbol/rename"
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
		RootsListChangedHandler: func(ctx context.Context, req *mcp.RootsListChangedRequest) {
			roots.Global.Sync(ctx, req.Session)
		},
	})

	return &Server{
		mcpServer:       s,
		cfg:             cfg,
		registeredTools: make(map[string]bool),
	}
}

// Run starts the MCP server using Stdio.
func (s *Server) Run(ctx context.Context) error {
	if err := s.RegisterHandlers(); err != nil {
		return err
	}
	return s.mcpServer.Run(ctx, &mcp.StdioTransport{})
}

// ServeHTTP starts the server over HTTP using StreamableHTTP.
func (s *Server) ServeHTTP(ctx context.Context, addr string) error {
	if err := s.RegisterHandlers(); err != nil {
		return err
	}

	handler := mcp.NewStreamableHTTPHandler(func(request *http.Request) *mcp.Server {
		return s.mcpServer
	}, nil)

	log.Printf("MCP HTTP Server starting on %s", addr)
	srv := &http.Server{
		Addr:    addr,
		Handler: handler,
	}

	go func() {
		<-ctx.Done()
		srv.Shutdown(context.Background())
	}()

	return srv.ListenAndServe()
}

// RegisterHandlers wires all tools, resources, and prompts.
func (s *Server) RegisterHandlers() error {
	type toolDef struct {
		name     string
		register func(*mcp.Server)
	}

	availableTools := []toolDef{
		{name: "go_docs", register: docs.Register},
		{name: "safe_shell", register: func(srv *mcp.Server) {
			run.Register(srv)
		}},
		{name: "code_review", register: func(srv *mcp.Server) {
			review.Register(srv, s.cfg.DefaultModel)
		}},
		{name: "file_read", register: read.Register},
		{name: "file_outline", register: outline.Register},
		{name: "symbol_inspect", register: inspect.Register},
		{name: "file_edit", register: edit.Register},
		{name: "file_create", register: create.Register},
		{name: "go_diff", register: diff.Register},
		{name: "go_modernize", register: modernize.Register},
		{name: "file_list", register: list.Register},
		{name: "go_build", register: build.Register},
		{name: "go_get", register: get.Register},
		{name: "go_test", register: test.Register},
		{name: "symbol_rename", register: rename.Register},
	}

	validTools := make(map[string]bool)
	for _, t := range availableTools {
		validTools[t.name] = true
		if s.cfg.IsToolEnabled(t.name) {
			t.register(s.mcpServer)
			s.registeredTools[t.name] = true

			// Track domain groups
			if strings.HasPrefix(t.name, "go_") {
				s.registeredTools["go"] = true
			}
			if strings.HasPrefix(t.name, "file_") {
				s.registeredTools["file"] = true
			}
			if strings.HasPrefix(t.name, "symbol_") {
				s.registeredTools["symbol"] = true
			}
		}
	}

	// Validate disabled tools
	for name := range s.cfg.DisabledTools {
		if !validTools[name] {
			return fmt.Errorf("unknown tool disabled: %s", name)
		}
	}

	// Register extra resources based on enabled domains
	if s.registeredTools["file"] || s.registeredTools["go"] {
		if !s.registeredTools["code"] {
			code.Register(s.mcpServer)
			s.registeredTools["code"] = true
		}
	}
	if s.registeredTools["symbol"] {
		symbol.Register(s.mcpServer)
		s.registeredTools["symbol"] = true
	}

	// Register extra resources based on enabled domains
	if !s.registeredTools["godoc"] {
		resgodoc.Register(s.mcpServer)
		s.registeredTools["godoc"] = true
	}

	// Register prompts
	if !s.registeredTools["prompt_import_this"] {
		s.mcpServer.AddPrompt(prompts.ImportThis("doc"), prompts.ImportThisHandler)
		s.registeredTools["prompt_import_this"] = true
	}

	return nil
}
