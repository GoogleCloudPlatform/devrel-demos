package cli

import (
	"log"
	"path/filepath"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/jobs"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func handleReevaluation(database *db.DB, cwd string, expID int64) {
	log.Printf("🧪 Re-evaluating runs for Experiment ID %d", expID)

	// Initialize basic runner (wsMgr not strictly needed for re-eval as we pass paths)
	// We need a dummy wsMgr to satisfy constructor
	// expDir and templatesDir will be resolved inside ReEvaluateExperiment
	// But ReEvaluateExperiment uses `os.Getwd()` to look for `experiments/runs` and `scenarios`.
	// We should ensure that matches `cwd`.

	// If cwd != os.Getwd(), the runner method might fail to find dirs.
	// But CLI usually runs from project root.

	// Dummy WSMgr
	wsMgr := workspace.New(cwd, filepath.Join(cwd, "scenarios"))
	r := runner.New(wsMgr, 1)
	r.SetDB(database)

	// Initialize Job Manager (implicitly done inside GetManager)
	jobs.GetManager().CreateJob("REVAL_CLI", map[string]interface{}{"experiment_id": expID})
	if err := r.ReEvaluateExperiment(expID, "cli-job-id"); err != nil {
		log.Fatalf("Re-evaluation failed: %v", err)
	}
	log.Println("Re-evaluation complete.")
}
