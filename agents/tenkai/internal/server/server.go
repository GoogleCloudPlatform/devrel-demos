package server

import (
	"fmt"
	"log"
	"net/http"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/server/handlers"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

type Server struct {
	api    *handlers.API
	router *http.ServeMux
}

func New(database *db.DB, r *runner.Runner, ws *workspace.Manager) *Server {
	api := handlers.New(database, r, ws)
	s := &Server{
		api:    api,
		router: http.NewServeMux(),
	}
	s.registerRoutes()
	return s
}

func (s *Server) Start(port int) error {
	addr := fmt.Sprintf(":%d", port)
	log.Printf("[Server] Listening on http://0.0.0.0:%d", port)

	// Chain middlewares: CORS -> Recovery -> Logger -> Router
	// Note: Middleware functions are now in middleware.go
	handler := CORSMiddleware(LoggerMiddleware(s.router))

	return http.ListenAndServe(addr, handler)
}
