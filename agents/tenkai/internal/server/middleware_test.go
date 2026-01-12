package server

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestCORSMiddleware(t *testing.T) {
	nextHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	handler := CORSMiddleware(nextHandler)

	req := httptest.NewRequest("GET", "/", nil)
	w := httptest.NewRecorder()

	handler.ServeHTTP(w, req)

	// Check Headers
	if w.Header().Get("Access-Control-Allow-Origin") != "*" {
		t.Errorf("Expected CORS Allow-Origin *, got %s", w.Header().Get("Access-Control-Allow-Origin"))
	}
	if w.Header().Get("Access-Control-Allow-Methods") == "" {
		t.Error("Expected CORS Allow-Methods to be set")
	}

	// Test OPTIONS
	reqOpt := httptest.NewRequest("OPTIONS", "/", nil)
	wOpt := httptest.NewRecorder()
	handler.ServeHTTP(wOpt, reqOpt)
	if wOpt.Code != http.StatusOK {
		t.Errorf("Expected 200 OK for OPTIONS, got %d", wOpt.Code)
	}
}

func TestLoggerMiddleware_Recovery(t *testing.T) {
	// Test Recovery from Panic
	panickingHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		panic("oops")
	})

	handler := LoggerMiddleware(panickingHandler)

	req := httptest.NewRequest("GET", "/", nil)
	w := httptest.NewRecorder()

	// Should not crash test
	func() {
		defer func() {
			if r := recover(); r != nil {
				t.Errorf("Middleware failed to recover from panic: %v", r)
			}
		}()
		handler.ServeHTTP(w, req)
	}()

	if w.Code != http.StatusInternalServerError {
		t.Errorf("Expected 500 Internal Server Error on panic, got %d", w.Code)
	}
}
