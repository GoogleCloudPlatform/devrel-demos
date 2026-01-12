package cli

import (
	"fmt"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/server"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func runServer(database *db.DB, cwd string, port int, concurrent int) {
	scenariosDir := filepath.Join(cwd, "scenarios")
	wsMgr := workspace.New(cwd, scenariosDir, scenariosDir)

	if concurrent <= 0 {
		concurrent = 4
	}

	r := runner.New(wsMgr, concurrent)
	r.SetDB(database)

	srv := server.New(database, r, wsMgr)

	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-c
		fmt.Println("\n[Tenkai Server] Shutting down...")
		os.Exit(0)
	}()

	if err := srv.Start(port); err != nil {
		log.Printf("Server failed: %v", err)
		os.Exit(1)
	}
}
