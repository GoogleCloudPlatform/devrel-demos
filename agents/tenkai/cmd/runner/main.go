package main

import (
	"context"
	"log"
	"os"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/storage"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func main() {
	log.Println("Starting Tenkai Runner (Worker Mode)...")

	dsn := os.Getenv("DB_DSN")
	if dsn == "" {
		log.Fatal("DB_DSN environment variable is required")
	}

	database, err := db.Open("pgx", dsn)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer database.Close()

	gcsBucket := os.Getenv("GCS_BUCKET")
	if gcsBucket == "" {
		log.Fatal("GCS_BUCKET environment variable is required")
	}

	// Scenarios and Templates handling
	scenariosDir := "/app/scenarios"
	templatesDir := "/app/templates"
	runsDir := "/tmp/tenkai-workspace/_runs"

	// Check for Cloud Run Volume Mount
	assetsDir := "/app/assets"
	if _, err := os.Stat(assetsDir); err == nil {
		log.Printf("Detected assets volume mount at %s", assetsDir)
		scenariosDir = assetsDir + "/scenarios"
		templatesDir = assetsDir + "/templates"
		runsDir = assetsDir + "/_runs"
	} else {
		if _, err := os.Stat(scenariosDir); os.IsNotExist(err) {
			// Fallback for local testing if not in container
			scenariosDir = "scenarios"
			templatesDir = "templates"
			runsDir = "_runs"
		}
	}

	log.Printf("Using runs directory: %s", runsDir)

	// Ephemeral workspace in /tmp
	wsMgr := workspace.New("/tmp/tenkai-workspace", templatesDir, runsDir, scenariosDir)

	// Initialize Runner
	r := runner.New(wsMgr, 1)
	r.SetMode(runner.ModeWorker)
	r.SetDB(database)

	st, err := storage.NewGCSStorage(context.Background(), gcsBucket, "")
	if err != nil {
		log.Fatalf("Failed to initialize GCS storage: %v", err)
	}
	r.SetStorage(st)

	// Create Worker instance
	// ID can be hostname or pod name
	workerID, _ := os.Hostname()
	w := runner.NewWorker(r, database, workerID)

	ctx := context.Background()
	log.Printf("Worker %s starting...", workerID)

	// Start handles env var reading (RUN_ID) and execution
	if err := w.Start(ctx); err != nil {
		log.Fatalf("Worker execution failed: %v", err)
	}

	log.Println("Worker completed successfully.")
}
