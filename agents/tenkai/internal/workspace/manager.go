package workspace

// Manager handles the creation and setup of isolated workspaces for experiments.
type Manager struct {
	BasePath      string
	TemplatesDirs []string
}

// New creates a new Workspace Manager.
func New(basePath string, templatesDirs ...string) *Manager {
	return &Manager{
		BasePath:      basePath,
		TemplatesDirs: templatesDirs,
	}
}
