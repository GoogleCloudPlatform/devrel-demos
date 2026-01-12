package handlers

import (
	"encoding/json"
	"log"
	"net/http"
	"strings"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

type API struct {
	DB     *db.DB
	Runner *runner.Runner
	WSMgr  *workspace.Manager
}

func New(database *db.DB, r *runner.Runner, ws *workspace.Manager) *API {
	return &API{
		DB:     database,
		Runner: r,
		WSMgr:  ws,
	}
}

// APIError represents a structured error response
type APIError struct {
	Status  int    `json:"-"`
	Message string `json:"error"`
}

func (e *APIError) Error() string {
	return e.Message
}

func NewAPIError(status int, msg string) *APIError {
	return &APIError{Status: status, Message: msg}
}

// Wrap converts a handler that returns (any, error) into a standard http.HandlerFunc
func (api *API) Wrap(h func(r *http.Request) (any, error)) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		data, err := h(r)
		if err != nil {
			status := http.StatusInternalServerError
			msg := err.Error()

			if apiErr, ok := err.(*APIError); ok {
				status = apiErr.Status
			} else if strings.Contains(msg, "not found") {
				status = http.StatusNotFound
			}

			log.Printf("[API Error] %s %s: %v", r.Method, r.URL.Path, err)

			w.WriteHeader(status)
			json.NewEncoder(w).Encode(map[string]string{"error": msg})
			return
		}

		if data == nil {
			// Go's json encoder handles nil interface as "null"
		}

		w.WriteHeader(http.StatusOK)
		if err := json.NewEncoder(w).Encode(data); err != nil {
			log.Printf("Failed to encode response: %v", err)
		}
	}
}
