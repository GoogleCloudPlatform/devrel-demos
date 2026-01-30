package main

import (
	"log"
	"os"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/cli"
)

func main() {
	cw, err := os.Getwd()
	if err != nil {
		log.Fatalf("Failed to get current working directory: %v", err)
	}

	cli.SetupLogging(cw)

	database, err := cli.InitDB(cw)
	if err != nil {
		log.Fatalf("Failed to open database: %v", err)
	}
	defer database.Close()

	flags := cli.ParseFlags()

	// Worker needs concurrent (default 1), port (for health check), gcsBucket (for artifacts)
	concurrency := 1
	if *flags.Concurrent > 0 {
		concurrency = *flags.Concurrent
	}

	gcsBucket := ""
	if flags.GCSBucket != nil {
		gcsBucket = *flags.GCSBucket
	}
	// Also Env Var GCS_BUCKET
	if gcsBucket == "" {
		gcsBucket = os.Getenv("GCS_BUCKET")
	}

	port := 8080
	if *flags.Port > 0 {
		port = *flags.Port
	}

	log.Println("Starting Tenkai Worker...")
	cli.RunWorker(database, cw, concurrency, port, gcsBucket)
}
