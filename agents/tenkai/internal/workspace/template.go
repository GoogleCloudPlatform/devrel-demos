package workspace

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"gopkg.in/yaml.v3"
)

// Template represents a reusable experiment configuration.
type Template struct {
	ID            string   `json:"id"`
	Name          string   `json:"name"`
	Description   string   `json:"description"`
	Path          string   `json:"path"`
	ConfigContent string   `json:"config_content,omitempty"` // For detail view
	AltCount      int      `json:"alt_count"`
	ScenCount     int      `json:"scen_count"`
	Alternatives  []string `json:"alternatives"`
	Reps          int      `json:"reps"`
	IsLocked      bool     `json:"is_locked"`
}

// ListTemplates returns a list of available templates found in the experiments/templates directory.
func (m *Manager) ListTemplates() []Template {
	var templates []Template

	// Assume standard location relative to BasePath
	templatesBase := m.ExperimentTemplatesDir
	if templatesBase == "" {
		templatesBase = filepath.Join(m.BasePath, "templates")
	}

	entries, err := os.ReadDir(templatesBase)

	if err != nil {
		// It's okay if it doesn't exist yet
		return templates
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		id := entry.Name()
		configPath := filepath.Join(templatesBase, id, "config.yaml")

		// Check if config.yaml exists to avoid noisy warnings for empty dirs
		if _, err := os.Stat(configPath); os.IsNotExist(err) {
			continue
		}

		// Parse config to get details
		cfg, err := config.Load(configPath)
		if err != nil {
			// CRITICAL: If a template in the repo is broken, we should know immediately.
			log.Fatalf("CRITICAL: failed to load template config %s: %v. Aborting startup.", configPath, err)
		}

		contentBytes, _ := os.ReadFile(configPath)

		tmpl := Template{
			ID:            id,
			Name:          cfg.Name,
			Description:   cfg.Description,
			Path:          configPath,
			ConfigContent: string(contentBytes),
			AltCount:      len(cfg.Alternatives),
			ScenCount:     len(cfg.Scenarios),
			Reps:          cfg.Repetitions,
			IsLocked:      cfg.IsLocked,
		}
		for _, a := range cfg.Alternatives {
			tmpl.Alternatives = append(tmpl.Alternatives, a.Name)
		}

		templates = append(templates, tmpl)
	}
	return templates
}

// GetTemplate returns the details of a specific template by ID.
func (m *Manager) GetTemplate(id string) (*Template, error) {
	templatesBase := m.ExperimentTemplatesDir
	if templatesBase == "" {
		templatesBase = filepath.Join(m.BasePath, "templates")
	}
	path := filepath.Join(templatesBase, id)

	configPath := filepath.Join(path, "config.yaml")

	if info, err := os.Stat(path); err == nil && info.IsDir() {
		// Found directory, now load config
		cfg, err := config.Load(configPath)
		if err != nil {
			return nil, fmt.Errorf("failed to load template config: %w", err)
		}

		contentBytes, _ := os.ReadFile(configPath)

		tmpl := &Template{
			ID:            id,
			Name:          cfg.Name,
			Description:   cfg.Description,
			Path:          configPath,
			ConfigContent: string(contentBytes),
			AltCount:      len(cfg.Alternatives),
			ScenCount:     len(cfg.Scenarios),
			Reps:          cfg.Repetitions,
			IsLocked:      cfg.IsLocked,
		}
		for _, a := range cfg.Alternatives {
			tmpl.Alternatives = append(tmpl.Alternatives, a.Name)
		}
		return tmpl, nil
	}

	return nil, fmt.Errorf("template %q not found", id)
}

// Helper to normalize configuration (e.g. inject default args)
func (m *Manager) normalizeConfig(content string) (string, error) {
	var cfg config.Configuration
	if err := yaml.Unmarshal([]byte(content), &cfg); err != nil {
		// If it's a partial config (template) it might not match Configuration struct exactly?
		// Template config should match.
		return content, nil
	}

	modified := false
	for i, alt := range cfg.Alternatives {
		if filepath.Base(alt.Command) == "gemini" {
			hasY := false
			hasO := false
			for idx, arg := range alt.Args {
				if arg == "-y" {
					hasY = true
				}
				if arg == "-o" && idx+1 < len(alt.Args) && alt.Args[idx+1] == "stream-json" {
					hasO = true
				}
			}
			if !hasY {
				// Prepend -y
				cfg.Alternatives[i].Args = append([]string{"-y"}, cfg.Alternatives[i].Args...)
				modified = true
			}
			if !hasO {
				// Append -o stream-json
				cfg.Alternatives[i].Args = append(cfg.Alternatives[i].Args, "-o", "stream-json")
				modified = true
			}
		}
	}

	if modified {
		data, err := yaml.Marshal(cfg)
		if err != nil {
			return "", err
		}
		return string(data), nil
	}
	return content, nil
}

// CreateTemplate creates a new template directory and config file.
func (m *Manager) CreateTemplate(name, description, configContent string, files map[string]string) (string, error) {
	templatesBase := m.ExperimentTemplatesDir
	if templatesBase == "" {
		templatesBase = filepath.Join(m.BasePath, "templates")
	}
	if err := os.MkdirAll(templatesBase, 0755); err != nil {

		return "", err
	}

	id := fmt.Sprintf("%d", GetTimestampID())

	tmplDir := filepath.Join(templatesBase, id)
	if err := os.MkdirAll(tmplDir, 0755); err != nil {
		return "", err
	}

	// Transactional cleanup: if function returns error, remove the dir
	success := false
	defer func() {
		if !success {
			os.RemoveAll(tmplDir)
		}
	}()

	// Normalize config content
	normConfig, err := m.normalizeConfig(configContent)
	if err != nil {
		return "", fmt.Errorf("failed to normalize config: %w", err)
	}

	// Write config.yaml
	if err := os.WriteFile(filepath.Join(tmplDir, "config.yaml"), []byte(normConfig), 0644); err != nil {
		return "", err
	}

	// Write extra files (SYSTEM.md, GEMINI.md, settings.json)
	for fname, content := range files {
		// Basic sanitization
		fname = filepath.Base(fname)
		if err := os.WriteFile(filepath.Join(tmplDir, fname), []byte(content), 0644); err != nil {
			return "", fmt.Errorf("failed to write file %s: %w", fname, err)
		}
	}

	success = true
	return id, nil
}

// UpdateTemplate updates an existing template configuration.
func (m *Manager) UpdateTemplate(id, configContent string, files map[string]string) error {
	templatesBase := m.ExperimentTemplatesDir
	if templatesBase == "" {
		templatesBase = filepath.Join(m.BasePath, "templates")
	}
	tmplDir := filepath.Join(templatesBase, id)

	configPath := filepath.Join(tmplDir, "config.yaml")

	if _, err := os.Stat(tmplDir); os.IsNotExist(err) {
		return fmt.Errorf("template %q not found", id)
	}

	// Normalize config content
	normConfig, err := m.normalizeConfig(configContent)
	if err != nil {
		return fmt.Errorf("failed to normalize config: %w", err)
	}

	// Write config.yaml
	if err := os.WriteFile(configPath, []byte(normConfig), 0644); err != nil {
		return err
	}

	// Write extra files
	for fname, content := range files {
		fname = filepath.Base(fname)
		if err := os.WriteFile(filepath.Join(tmplDir, fname), []byte(content), 0644); err != nil {
			return fmt.Errorf("failed to write file %s: %w", fname, err)
		}
	}
	return nil
}

// DeleteTemplate deletes a template directory.
func (m *Manager) DeleteTemplate(id string) error {
	templatesBase := m.ExperimentTemplatesDir
	if templatesBase == "" {
		templatesBase = filepath.Join(m.BasePath, "templates")
	}
	path := filepath.Join(templatesBase, id)

	if _, err := os.Stat(path); err == nil {

		return os.RemoveAll(path)
	}
	return fmt.Errorf("template %q not found", id)
}

// DeleteAllTemplates deletes all templates.
func (m *Manager) DeleteAllTemplates() error {
	templatesBase := m.ExperimentTemplatesDir
	if templatesBase == "" {
		templatesBase = filepath.Join(m.BasePath, "templates")
	}
	entries, err := os.ReadDir(templatesBase)

	if err != nil {
		return nil // Ignore if dir doesn't exist
	}
	for _, entry := range entries {
		if entry.IsDir() {
			os.RemoveAll(filepath.Join(templatesBase, entry.Name()))
		}
	}
	return nil
}

// Helper for ID generation

func GetTimestampID() int64 {
	return time.Now().UnixNano()
}

// CreateTemplate creates a new template directory and config file.
