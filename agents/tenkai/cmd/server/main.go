package main

import (
	"log"
	"os"
	"strconv"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/server"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func main() {
	log.Println("Starting Tenkai Server (Orchestrator)...")

	// Database Connection
	dsn := os.Getenv("DB_DSN")
	if dsn == "" {
		log.Fatalf("DB_DSN environment variable is required")
	}

	// Open DB (pgx)
	database, err := db.Open("pgx", dsn)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	defer database.Close()

	// Initialize Workspace Manager
	// Default paths (baked into image or local fallback)
	scenariosDir := "/app/scenarios"
	templatesDir := "/app/templates"
	runsDir := "/tmp/tenkai-server/_runs"

	// Check for Cloud Run Volume Mount
	assetsDir := "/app/assets"
	if _, err := os.Stat(assetsDir); err == nil {
		log.Printf("Detected assets volume mount at %s", assetsDir)
		scenariosDir = assetsDir + "/scenarios"
		templatesDir = assetsDir + "/templates"
		runsDir = assetsDir + "/_runs"
	} else {
		// Fallback for local dev if /app/scenarios doesn't exist
		if _, err := os.Stat(scenariosDir); os.IsNotExist(err) {
			cwd, _ := os.Getwd()
			scenariosDir = cwd + "/scenarios"
			templatesDir = cwd + "/templates"
			runsDir = cwd + "/_runs"
		}
	}

	log.Printf("Using scenarios from: %s", scenariosDir)
	log.Printf("Using templates from: %s", templatesDir)
	log.Printf("Using runs directory: %s", runsDir)

	// Server doesn't write code, but needs to read templates
	wsMgr := workspace.New("/tmp/tenkai-server", templatesDir, runsDir, scenariosDir)

	// Initialize Runner (Orchestrator Mode)
	// Server doesn't run code itself, it dispatches jobs
	concurrent := 100 // Limit for detached job dispatch
	if c := os.Getenv("MAX_CONCURRENT"); c != "" {
		if val, err := strconv.Atoi(c); err == nil {
			concurrent = val
		}
	}

	r := runner.New(wsMgr, concurrent)
	r.SetMode(runner.ModeServer)
	r.SetDB(database)

	// Start Web Server
	port := 8080
	if p := os.Getenv("PORT"); p != "" {
		if val, err := strconv.Atoi(p); err == nil {
			port = val
		}
	}

	srv := server.New(database, r, wsMgr)
	if err := srv.Start(port); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
