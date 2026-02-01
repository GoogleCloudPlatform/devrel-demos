package workspace

// Manager handles the creation and setup of isolated workspaces for experiments.
type Manager struct {
	BasePath               string
	ScenariosDirs          []string
	ExperimentTemplatesDir string
	RunsDir                string
}

// New creates a new Workspace Manager.
func New(basePath string, experimentTemplatesDir string, runsDir string, scenariosDirs ...string) *Manager {
	return &Manager{
		BasePath:               basePath,
		ExperimentTemplatesDir: experimentTemplatesDir,
		RunsDir:                runsDir,
		ScenariosDirs:          scenariosDirs,
	}
}
