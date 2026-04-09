package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"cloud.google.com/go/storage"
)

type PingResponse struct {
	Message   string    `json:"message"`
	Timestamp time.Time `json:"timestamp"`
	BackendID string    `json:"backend_id"`
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	http.HandleFunc("/ping", pingHandler)
	http.HandleFunc("/health", healthHandler)

	fmt.Printf("Backend listening on port %s\n", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatal(err)
	}
}

func pingHandler(w http.ResponseWriter, r *http.Request) {
	hostname, _ := os.Hostname()

	// Read the body to get the size
	body, err := io.ReadAll(r.Body)
	if err != nil {
		log.Printf("ERROR: Failed to read body: %v\n", err)
	}
	defer r.Body.Close()

	mode := r.URL.Query().Get("mode")
	gcsMessage := ""

	if mode == "gcs" {
		bucketName := os.Getenv("BUCKET_NAME")
		destBucketName := os.Getenv("DEST_BUCKET_NAME")

		if bucketName == "" || destBucketName == "" {
			log.Println("ERROR: BUCKET_NAME or DEST_BUCKET_NAME not set")
			gcsMessage = "GCS mode failed: environment variables not set"
		} else {
			ctx := context.Background()
			client, err := storage.NewClient(ctx)
			if err != nil {
				log.Printf("ERROR: Failed to create storage client: %v\n", err)
				gcsMessage = fmt.Sprintf("GCS mode failed: %v", err)
			} else {
				defer client.Close()

				objectName := fmt.Sprintf("ping-%d-%s", time.Now().UnixNano(), hostname)
				
				// 1. Create object in GCS
				wc := client.Bucket(bucketName).Object(objectName).NewWriter(ctx)
				if _, err := wc.Write(body); err != nil {
					log.Printf("ERROR: Failed to write to GCS: %v\n", err)
					gcsMessage = fmt.Sprintf("GCS write failed: %v", err)
				} else if err := wc.Close(); err != nil {
					log.Printf("ERROR: Failed to close GCS writer: %v\n", err)
					gcsMessage = fmt.Sprintf("GCS close failed: %v", err)
				} else {
					// 2. Copy file to destination region
					src := client.Bucket(bucketName).Object(objectName)
					dst := client.Bucket(destBucketName).Object(objectName)
					
					if _, err := dst.CopierFrom(src).Run(ctx); err != nil {
						log.Printf("ERROR: Failed to copy in GCS: %v\n", err)
						gcsMessage = fmt.Sprintf("GCS copy failed: %v", err)
					} else {
						gcsMessage = fmt.Sprintf("Successfully transferred %d bytes from %s to %s", len(body), bucketName, destBucketName)
					}
				}
			}
		}
	}

	msg := fmt.Sprintf("pong from backend (received %d bytes)", len(body))
	if gcsMessage != "" {
		msg += " | " + gcsMessage
	}

	resp := PingResponse{
		Message:   msg,
		Timestamp: time.Now(),
		BackendID: hostname,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("OK"))
}
