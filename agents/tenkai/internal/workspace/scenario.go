package workspace

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"gopkg.in/yaml.v3"
)

// Scenario represents a discoverable scenario.
type Scenario struct {
	ID          string                  `json:"id"`
	Name        string                  `json:"name"`
	Description string                  `json:"description"`
	Locked      bool                    `json:"locked"`
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
				scen.Locked = cfg.Locked
				scen.Task = cfg.Task
				scen.Assets = cfg.Assets
				scen.Validation = cfg.Validation
			}

			scenarios = append(scenarios, scen)
			seen[name] = true
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
				scen.Locked = cfg.Locked
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
func (m *Manager) CreateScenario(name, description, task string, assets []config.Asset, validation []config.ValidationRule, env map[string]string) (string, error) {
	// Use the first templates dir for creation (usually scenarios/)
	if len(m.TemplatesDirs) == 0 {
		return "", fmt.Errorf("no templates directory configured")
	}
	baseDir := m.TemplatesDirs[0]

	// Find next sequential ID
	entries, _ := os.ReadDir(baseDir)
	maxID := 0
	for _, entry := range entries {
		if entry.IsDir() {
			if id, err := strconv.Atoi(entry.Name()); err == nil {
				if id > maxID {
					maxID = id
				}
			}
		}
	}
	id := fmt.Sprintf("%d", maxID+1)

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
		Env:         env,
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
func (m *Manager) UpdateScenario(id, name, description, task string, validation []config.ValidationRule, assets []config.Asset, env map[string]string) error {
	for _, dir := range m.TemplatesDirs {
		path := filepath.Join(dir, id)
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			// Update scenario.yaml
			configPath := filepath.Join(path, "scenario.yaml")
			var cfg config.ScenarioConfig
			if existing, err := config.LoadScenarioConfig(configPath); err == nil {
				cfg = *existing
			}

			// Update fields
			cfg.Name = name
			cfg.Description = description
			if task != "" {
				cfg.Task = task
			}
			cfg.Validation = validation
			if env != nil {
				cfg.Env = env
			}

			// Append new assets if any
			// Note: This appends. It doesn't replace existing unless logic is added.
			// Ideally we might want to merge or allow full replacement.
			// For now, let's append new ones which seems to be the intent of "uploading files".
			// But we also need to handle the file persistence.

			// Process new assets
			for i := range assets {
				asset := &assets[i]
				if asset.Type == "file" && asset.Content != "" {
					relPath := filepath.Clean(asset.Target)
					if filepath.IsAbs(relPath) || strings.HasPrefix(relPath, "..") {
						relPath = strings.TrimPrefix(relPath, "/")
						relPath = strings.ReplaceAll(relPath, "../", "")
					}

					if relPath == "." || relPath == "" {
						continue
					}

					savePath := filepath.Join(path, relPath)

					if err := os.MkdirAll(filepath.Dir(savePath), 0755); err != nil {
						return fmt.Errorf("failed to create directory for asset %s: %w", relPath, err)
					}

					if err := os.WriteFile(savePath, []byte(asset.Content), 0644); err != nil {
						return fmt.Errorf("failed to write asset %s: %w", relPath, err)
					}

					asset.Source = relPath
					asset.Content = ""
				}

				// Check if asset exists and replace it
				found := false
				for j := range cfg.Assets {
					if cfg.Assets[j].Target == asset.Target {
						cfg.Assets[j] = *asset
						found = true
						break
					}
				}
				if !found {
					cfg.Assets = append(cfg.Assets, *asset)
				}
			}

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

// LockScenario updates the locked status of a scenario.
func (m *Manager) LockScenario(id string, locked bool) error {
	for _, dir := range m.TemplatesDirs {
		path := filepath.Join(dir, id)
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			configPath := filepath.Join(path, "scenario.yaml")
			var cfg config.ScenarioConfig
			if existing, err := config.LoadScenarioConfig(configPath); err == nil {
				cfg = *existing
			} else {
				// If no config exists, we can't lock it properly without creating one?
				// Or we should fail? Assuming scenario usually has config.
				return fmt.Errorf("failed to load scenario config: %w", err)
			}

			cfg.Locked = locked

			data, err := yaml.Marshal(cfg)
			if err != nil {
				return err
			}

			return os.WriteFile(configPath, data, 0644)
		}
	}
	return fmt.Errorf("scenario %q not found", id)
}

// DeleteScenario deletes a scenario directory.
func (m *Manager) DeleteScenario(id string) error {
	for _, dir := range m.TemplatesDirs {
		path := filepath.Join(dir, id)
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			configPath := filepath.Join(path, "scenario.yaml")
			if cfg, err := config.LoadScenarioConfig(configPath); err == nil {
				if cfg.Locked {
					return fmt.Errorf("scenario is locked")
				}
			}
			return os.RemoveAll(path)
		}
	}
	return fmt.Errorf("scenario %q not found", id)
}

// DeleteAllScenarios deletes all scenarios.
func (m *Manager) DeleteAllScenarios() error {
	for _, dir := range m.TemplatesDirs {
		entries, err := os.ReadDir(dir)
		if err != nil {
			continue
		}
		for _, entry := range entries {
			if entry.IsDir() {
				path := filepath.Join(dir, entry.Name())
				configPath := filepath.Join(path, "scenario.yaml")

				// Only delete if it looks like a scenario
				if _, err := os.Stat(configPath); err == nil {
					// Check if locked
					if cfg, err := config.LoadScenarioConfig(configPath); err == nil && cfg.Locked {
						continue
					}
					os.RemoveAll(path)
				}
			}
		}
	}
	return nil
}
