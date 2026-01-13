package workspace

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"gopkg.in/yaml.v3"
)

// Scenario represents a discoverable scenario.
type Scenario struct {
	ID          string                  `json:"id"`
	Name        string                  `json:"name"`
	Description string                  `json:"description"`
	Path        string                  `json:"path"`
	Task        string                  `json:"task,omitempty"`
	Assets      []config.Asset          `json:"assets,omitempty"`
	Validation  []config.ValidationRule `json:"validation,omitempty"`
}

// ListScenarios returns a list of available scenarios found in the templates directories.
func (m *Manager) ListScenarios() []Scenario {
	var scenarios []Scenario
	seen := make(map[string]bool)

	for _, dir := range m.TemplatesDirs {
		entries, err := os.ReadDir(dir)
		if err != nil {
			log.Printf("Warning: failed to read templates dir %s: %v", dir, err)
			continue
		}

		for _, entry := range entries {
			if !entry.IsDir() {
				continue
			}

			name := entry.Name()
			if seen[name] {
				continue
			}

			// Check for scenario.yaml to get description
			scen := Scenario{
				ID:   name,
				Name: name, // Default
				Path: filepath.Join(dir, name),
			}

			configPath := filepath.Join(dir, name, "scenario.yaml")
			            if cfg, err := config.LoadScenarioConfig(configPath); err == nil {
			                if cfg.Name != "" {
			                    scen.Name = cfg.Name
			                }
			                scen.Description = cfg.Description
			                scen.Task = cfg.Task
			                scen.Assets = cfg.Assets
			                scen.Validation = cfg.Validation
			            }
			
			            scenarios = append(scenarios, scen)			seen[name] = true
		}
	}
	return scenarios
}

// GetScenario returns the details of a specific scenario by ID.
func (m *Manager) GetScenario(id string) (*Scenario, error) {
	for _, dir := range m.TemplatesDirs {
		path := filepath.Join(dir, id)
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			scen := &Scenario{
				ID:   id,
				Name: id,
				Path: path,
			}

			configPath := filepath.Join(path, "scenario.yaml")
			if cfg, err := config.LoadScenarioConfig(configPath); err == nil {
				if cfg.Name != "" {
					scen.Name = cfg.Name
				}
				scen.Description = cfg.Description
				scen.Task = cfg.Task
				scen.Assets = cfg.Assets
				scen.Validation = cfg.Validation
			}
			return scen, nil
		}
	}
	return nil, fmt.Errorf("scenario %q not found", id)
}

// CreateScenario creates a new scenario directory and assets.
func (m *Manager) CreateScenario(name, description, task string, assets []config.Asset, validation []config.ValidationRule) (string, error) {
	// Use the first templates dir for creation (usually scenarios/)
	if len(m.TemplatesDirs) == 0 {
		return "", fmt.Errorf("no templates directory configured")
	}
	baseDir := m.TemplatesDirs[0]

	id := fmt.Sprintf("%d", time.Now().UnixNano())

	scenDir := filepath.Join(baseDir, id)
	if err := os.MkdirAll(scenDir, 0755); err != nil {
		return "", err
	}

	// Create scenario.yaml
	cfg := config.ScenarioConfig{
		Name:        name,
		Description: description,
		Task:        task,
		Assets:      assets,
		Validation:  validation,
	}

	// Persist file assets to disk instead of embedding in YAML
	for i := range cfg.Assets {
		asset := &cfg.Assets[i]
		if asset.Type == "file" && asset.Content != "" {
			// Clean the target path to prevent traversal
			relPath := filepath.Clean(asset.Target)
			if filepath.IsAbs(relPath) || strings.HasPrefix(relPath, "..") {
				// Sanitize: strip leading /, .., or invalid chars if needed.
				// For now, just taking the base name might be too restrictive if folder structure is desired.
				// Let's assume Target is trusted enough or just strip ".."
				relPath = strings.TrimPrefix(relPath, "/")
				relPath = strings.ReplaceAll(relPath, "../", "")
			}

			if relPath == "." || relPath == "" {
				// Skip if invalid target
				continue
			}

			savePath := filepath.Join(scenDir, relPath)

			if err := os.MkdirAll(filepath.Dir(savePath), 0755); err != nil {
				return "", fmt.Errorf("failed to create directory for asset %s: %w", relPath, err)
			}

			if err := os.WriteFile(savePath, []byte(asset.Content), 0644); err != nil {
				return "", fmt.Errorf("failed to write asset %s: %w", relPath, err)
			}

			asset.Source = relPath
			asset.Content = ""
		}
	}

	data, err := yaml.Marshal(cfg)
	if err != nil {
		return "", err
	}

	if err := os.WriteFile(filepath.Join(scenDir, "scenario.yaml"), data, 0644); err != nil {
		return "", err
	}

	// Also write PROMPT.md for easier reading
	if task != "" {
		if err := os.WriteFile(filepath.Join(scenDir, "PROMPT.md"), []byte(task), 0644); err != nil {
			return "", err
		}
	}
	return id, nil
}

// UpdateScenario updates an existing scenario configuration.
func (m *Manager) UpdateScenario(id, name, description, task string, validation []config.ValidationRule) error {
	for _, dir := range m.TemplatesDirs {
		path := filepath.Join(dir, id)
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			// Update scenario.yaml
			configPath := filepath.Join(path, "scenario.yaml")
			var cfg config.ScenarioConfig
			if existing, err := config.LoadScenarioConfig(configPath); err == nil {
				cfg = *existing // Preserve assets and other fields not being updated
			}

			// Update fields
			cfg.Name = name
			cfg.Description = description
			if task != "" {
				cfg.Task = task
			}
			cfg.Validation = validation

			data, err := yaml.Marshal(cfg)
			if err != nil {
				return err
			}

			if err := os.WriteFile(configPath, data, 0644); err != nil {
				return err
			}

			// Update PROMPT.md if task changed
			if task != "" {
				if err := os.WriteFile(filepath.Join(path, "PROMPT.md"), []byte(task), 0644); err != nil {
					return err
				}
			}
			return nil
		}
	}
	return fmt.Errorf("scenario %q not found", id)
}

// DeleteScenario deletes a scenario directory.
func (m *Manager) DeleteScenario(id string) error {
	for _, dir := range m.TemplatesDirs {
		path := filepath.Join(dir, id)
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			return os.RemoveAll(path)
		}
	}
	return fmt.Errorf("scenario %q not found", id)
}
