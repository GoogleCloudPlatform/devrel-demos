package server

import (
	"encoding/json"
	"log"
	"net/http"
)

type Handler func(w http.ResponseWriter, r *http.Request) error

func (h Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if err := h(w, r); err != nil {
		// Log the error (slog or standard log)
		log.Printf("HTTP error: %v", err)
		
		// Return generic error to user
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
	}
}

func NewServer() http.Handler {
	mux := http.NewServeMux()
	addRoutes(mux)
	var handler http.Handler = mux
	return handler
}

func addRoutes(mux *http.ServeMux) {
	mux.Handle("GET /", Handler(handleIndex))
	mux.Handle("GET /health", Handler(handleHealth))
}

func handleIndex(w http.ResponseWriter, r *http.Request) error {
	w.WriteHeader(http.StatusOK)
	_, err := w.Write([]byte("Hello, World!"))
	return err
}

func handleHealth(w http.ResponseWriter, r *http.Request) error {
	return json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}