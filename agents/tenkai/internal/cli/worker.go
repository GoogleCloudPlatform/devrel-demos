package cli

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/storage"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func RunWorker(database *db.DB, cwd string, concurrent int, port int, gcsBucket string) {
	hostname, _ := os.Hostname()
	workerID := fmt.Sprintf("worker-%s-%d", hostname, os.Getpid())
	log.Printf("Starting worker %s...", workerID)

	scenariosDir := filepath.Join(cwd, "scenarios")
	wsMgr := workspace.New(cwd, scenariosDir, scenariosDir)

	concurrency := 1
	if concurrent > 0 {
		concurrency = concurrent
	}

	r := runner.New(wsMgr, concurrency)
	r.SetDB(database)

	if gcsBucket != "" {
		ctx := context.Background()
		st, err := storage.NewGCSStorage(ctx, gcsBucket, "")
		if err != nil {
			log.Fatalf("Failed to init GCS storage: %v", err)
		}
		r.SetStorage(st)
		log.Printf("Using GCS Bucket: %s", gcsBucket)
	} else {
		r.SetStorage(storage.NewDBStorage(database))
		log.Printf("Using DB Storage for artifacts")
	}

	w := runner.NewWorker(r, database, workerID)
	// Start dummy HTTP server for Cloud Run health checks
	go func() {
		addr := fmt.Sprintf(":%d", port)
		log.Printf("Worker listening on %s (health check)", addr)
		// Simple handler that returns 200 OK
		http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusOK)
			fmt.Fprintln(w, "OK")
		})
		if err := http.ListenAndServe(addr, nil); err != nil {
			log.Printf("Worker HTTP server failed: %v", err)
		}
	}()

	if err := w.Start(context.Background()); err != nil {
		log.Fatalf("Worker failed: %v", err)
	}
}
