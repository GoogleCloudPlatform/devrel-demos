package tools

import (
	"bytes"
	"log"
	"net/http"

	"github.com/felixge/httpsnoop"
)

func LocalhostCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Set headers to allow all origins
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		// Handle preflight "OPTIONS" requests
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

type requestLogger struct {
	body   *bytes.Buffer
	status int
}

// LogHandler logs the request, status code, and response body on error.
// uses the default logger.
func LogHandler(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		l := requestLogger{
			body:   &bytes.Buffer{},
			status: http.StatusOK,
		}
		wp := httpsnoop.Wrap(w, httpsnoop.Hooks{
			WriteHeader: func(whf httpsnoop.WriteHeaderFunc) httpsnoop.WriteHeaderFunc {
				return func(code int) {
					l.status = code
					w.WriteHeader(code)
				}
			},
			Write: func(wf httpsnoop.WriteFunc) httpsnoop.WriteFunc {
				return func(b []byte) (int, error) {
					l.body.Write(b)
					return w.Write(b)
				}
			},
		})
		h.ServeHTTP(wp, r)
		log.Printf("%s %s %d\n", r.Method, r.RequestURI, l.status)
		if l.status > 400 {
			log.Println(l.body.String())
		}
	})

}
