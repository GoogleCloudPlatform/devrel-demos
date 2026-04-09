package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	backendURL := os.Getenv("BACKEND_URL")
	if backendURL == "" {
		log.Println("WARNING: BACKEND_URL not set")
	}

	http.HandleFunc("/", serveIndex)
	http.HandleFunc("/api/config", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"backend_url": backendURL})
	})
	http.HandleFunc("/api/ping", func(w http.ResponseWriter, r *http.Request) {
		proxyToBackend(w, r, backendURL)
	})
	http.HandleFunc("/api/batch-ping", func(w http.ResponseWriter, r *http.Request) {
		handleBatchPing(w, r, backendURL)
	})

	fmt.Printf("Frontend listening on port %s\n", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatal(err)
	}
}

func serveIndex(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	http.ServeFile(w, r, "static/index.html")
}

func proxyToBackend(w http.ResponseWriter, r *http.Request, backendURL string) {
	if backendURL == "" {
		http.Error(w, "Backend URL not configured", http.StatusInternalServerError)
		return
	}

	sizeStr := r.URL.Query().Get("size")
	size := 0
	if sizeStr != "" {
		fmt.Sscanf(sizeStr, "%d", &size)
	}

	mode := r.URL.Query().Get("mode")

	data, err := callBackendPing(backendURL, size, mode)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(data)
}

type BatchResult struct {
	Total    int            `json:"total"`
	Success  int            `json:"success"`
	Failure  int            `json:"failure"`
	Backends map[string]int `json:"backends"`
}

func handleBatchPing(w http.ResponseWriter, r *http.Request, backendURL string) {
	if backendURL == "" {
		http.Error(w, "Backend URL not configured", http.StatusInternalServerError)
		return
	}

	countStr := r.URL.Query().Get("count")
	count := 10
	if countStr != "" {
		fmt.Sscanf(countStr, "%d", &count)
	}
	if count > 2000 {
		count = 2000 // Cap at 2000
	}

	sizeStr := r.URL.Query().Get("size")
	size := 0
	if sizeStr != "" {
		fmt.Sscanf(sizeStr, "%d", &size)
	}

	mode := r.URL.Query().Get("mode")

	results := make(chan string, count)

	// Use a worker pool or semaphore to throttle concurrency to 50
	sem := make(chan struct{}, 50)

	for i := 0; i < count; i++ {
		go func() {
			sem <- struct{}{}        // Acquire
			defer func() { <-sem }() // Release

			data, err := callBackendPing(backendURL, size, mode)
			if err != nil {
				results <- "error"
				return
			}
			parts := strings.Split(string(data), "\"backend_id\":\"")
			if len(parts) > 1 {
				id := strings.Split(parts[1], "\"")[0]
				results <- id
			} else {
				results <- "unknown"
			}
		}()
	}

	batch := BatchResult{
		Total:    count,
		Backends: make(map[string]int),
	}

	for i := 0; i < count; i++ {
		res := <-results
		if res == "error" {
			batch.Failure++
		} else {
			batch.Success++
			batch.Backends[res]++
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(batch)
}

func callBackendPing(backendURL string, size int, mode string) ([]byte, error) {
	// Fetch OIDC token from metadata server
	token, err := getOIDCToken(backendURL)
	if err != nil {
		log.Printf("ERROR: Failed to fetch OIDC token: %v\n", err)
	}

	var body io.Reader
	method := "GET"
	if size > 0 {
		method = "POST"
		payload := generatePayload(size)
		body = strings.NewReader(payload)
	}

	url := backendURL + "/ping"
	if mode != "" {
		url += "?mode=" + mode
	}

	req, err := http.NewRequest(method, url, body)
	if err != nil {
		return nil, err
	}

	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("backend returned status %d", resp.StatusCode)
	}

	return io.ReadAll(resp.Body)
}

func generatePayload(size int) string {
	lorem := "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
	if size <= 0 {
		return ""
	}
	var b strings.Builder
	for b.Len() < size {
		b.WriteString(lorem)
	}
	res := b.String()
	if len(res) > size {
		return res[:size]
	}
	return res
}

func getOIDCToken(audience string) (string, error) {
	// Only works on GCP (Cloud Run, GCE, etc.)
	url := fmt.Sprintf("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience=%s", audience)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}
	req.Header.Add("Metadata-Flavor", "Google")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("metadata server returned status %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	return strings.TrimSpace(string(body)), nil
}
