package cli

import (
	"fmt"
	"log"
	"os"
	"strings"
	"syscall"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
)

func cleanupOrphanExperiments(database *db.DB) {
	experiments, err := database.GetExperiments()
	if err != nil {
		log.Printf("Warning: failed to fetch experiments for cleanup: %v", err)
		return
	}

	count := 0
	for _, exp := range experiments {
		status := strings.ToUpper(exp.Status)
		if status == db.ExperimentStatusRunning {
			if exp.PID <= 0 {
				continue
			}

			// On Unix, FindProcess always succeeds, we must call Signal(0)
			process, err := os.FindProcess(exp.PID)
			if err != nil {
				markAbortedSpeculative(database, exp)
				count++
				continue
			}

			err = process.Signal(syscall.Signal(0))
			if err != nil {
				// Signal 0 failed, process is likely dead
				markAbortedSpeculative(database, exp)
				count++
			}
		}
	}
	if count > 0 {
		fmt.Printf("Cleaned up %d orphaned experiment(s).\n", count)
	}
}

func markAbortedSpeculative(database *db.DB, exp models.Experiment) {
	log.Printf("Detected orphaned experiment %d (PID %d is dead). Marking as ABORTED.", exp.ID, exp.PID)
	database.UpdateExperimentStatus(exp.ID, db.ExperimentStatusAborted)
	database.UpdateExperimentError(exp.ID, "Orchestrator process terminated unexpectedly")

	// Also mark non-terminal runs as ABORTED
	results, err := database.GetRunResults(exp.ID, -1, 0)
	if err == nil {
		for _, r := range results {
			st := strings.ToUpper(r.Status)
			if st == db.RunStatusRunning || st == db.RunStatusQueued {
				database.UpdateRunStatusAndReason(r.ID, db.RunStatusAborted, "ORPHANED")
			}
		}
	}
}
