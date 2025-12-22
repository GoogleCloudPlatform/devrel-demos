package workspace

import (
	"archive/zip"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
)

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

// PrepareWorkspace creates an isolated workspace for a specific run.
// Structure: <experimentDir>/<alternative>/<scenario>/<repetition>
func (m *Manager) PrepareWorkspace(experimentDir, alternative, scenario string, repetition int, settingsPath, contextFilePath string, policyFiles []string) (string, error) {
	wsPath := filepath.Join(experimentDir, alternative, scenario, fmt.Sprintf("rep-%d", repetition))

	if err := os.MkdirAll(wsPath, 0755); err != nil {
		return "", fmt.Errorf("failed to create workspace directory: %w", err)
	}

	// Copy template content
	var tmplPath string
	for _, dir := range m.TemplatesDirs {
		path := filepath.Join(dir, scenario)
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			tmplPath = path
			break
		}
	}

	if tmplPath == "" {
		return "", fmt.Errorf("scenario template %q not found in any of: %v", scenario, m.TemplatesDirs)
	}

	// Check for scenario.yaml
	scenarioConfigPath := filepath.Join(tmplPath, "scenario.yaml")
	if _, err := os.Stat(scenarioConfigPath); err == nil {
		// Scenario-as-Code mode
		log.Printf("Loading scenario configuration from %s", scenarioConfigPath)
		scenCfg, err := config.LoadScenarioConfig(scenarioConfigPath)
		if err != nil {
			return "", fmt.Errorf("failed to load scenario config: %w", err)
		}

		// Process Assets
		for _, asset := range scenCfg.Assets {
			targetPath := filepath.Join(wsPath, asset.Target) // Target is relative to wsPath
			if asset.Target == "." {
				targetPath = wsPath
			}

			switch asset.Type {
			case "directory":
				src := filepath.Join(tmplPath, asset.Source)
				if err := copyDir(src, targetPath); err != nil {
					return "", fmt.Errorf("failed to copy directory asset %s: %w", src, err)
				}
			case "file":
				if asset.Content != "" {
					// Inline content
					if err := os.WriteFile(targetPath, []byte(asset.Content), 0644); err != nil {
						return "", fmt.Errorf("failed to write inline file asset %s: %w", targetPath, err)
					}
				} else {
					// Copy from source
					src := filepath.Join(tmplPath, asset.Source)
					if err := copyFile(src, targetPath); err != nil {
						return "", fmt.Errorf("failed to copy file asset %s: %w", src, err)
					}
				}
			case "git":
				if err := setupGit(asset.Source, asset.Ref, targetPath); err != nil {
					return "", fmt.Errorf("failed to setup git asset %s: %w", asset.Source, err)
				}
			case "zip":
				if err := setupZip(asset.Source, targetPath); err != nil {
					return "", fmt.Errorf("failed to setup zip asset %s: %w", asset.Source, err)
				}
			}
		}

		// Generate PROMPT.md
		promptContent := scenCfg.Task
		if scenCfg.GithubIssue != "" {
			issueContent, err := fetchGithubIssue(scenCfg.GithubIssue)
			if err != nil {
				log.Printf("Warning: failed to fetch GitHub issue: %v", err)
				promptContent += fmt.Sprintf("\n\n(Failed to fetch issue context: %v)", err)
			} else {
				promptContent = fmt.Sprintf("# Task from GitHub Issue: %s\n\n**Title**: %s\n\n**Description**:\n%s\n\n%s",
					scenCfg.GithubIssue, issueContent.Title, issueContent.Body, promptContent)
			}
		}

		if promptContent != "" {
			if err := os.WriteFile(filepath.Join(wsPath, "PROMPT.md"), []byte(promptContent), 0644); err != nil {
				return "", fmt.Errorf("failed to write PROMPT.md: %w", err)
			}
		}

	} else {
		// Legacy mode: Copy entire directory
		if err := copyDir(tmplPath, wsPath); err != nil {
			return "", fmt.Errorf("failed to copy template from %s to %s: %w", tmplPath, wsPath, err)
		}
	}

	// Handle MCP settings if provided
	if settingsPath != "" {
		geminiDir := filepath.Join(wsPath, ".gemini")
		if err := os.MkdirAll(geminiDir, 0755); err != nil {
			return "", fmt.Errorf("failed to create .gemini directory: %w", err)
		}

		destSettings := filepath.Join(geminiDir, "settings.json")
		if err := copyFile(settingsPath, destSettings); err != nil {
			return "", fmt.Errorf("failed to create settings file: %w", err)
		}
	}

	// Handle Context File (GEMINI.md) if provided
	if contextFilePath != "" {
		destContext := filepath.Join(wsPath, "GEMINI.md")
		if err := copyFile(contextFilePath, destContext); err != nil {
			return "", fmt.Errorf("failed to copy context file: %w", err)
		}
	}

	// Handle Policy Files if provided
	if len(policyFiles) > 0 {
		policiesDir := filepath.Join(wsPath, ".gemini", "policies")
		if err := os.MkdirAll(policiesDir, 0755); err != nil {
			return "", fmt.Errorf("failed to create policies directory: %w", err)
		}

		for _, pf := range policyFiles {
			destPolicy := filepath.Join(policiesDir, filepath.Base(pf))
			if err := copyFile(pf, destPolicy); err != nil {
				return "", fmt.Errorf("failed to copy policy file %s: %w", pf, err)
			}
		}
	}

	return wsPath, nil
}

func copyDir(src, dst string) error {
	entries, err := os.ReadDir(src)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		dstPath := filepath.Join(dst, entry.Name())

		if entry.IsDir() {
			if err := os.MkdirAll(dstPath, 0755); err != nil {
				return err
			}
			if err := copyDir(srcPath, dstPath); err != nil {
				return err
			}
		} else {
			if err := copyFile(srcPath, dstPath); err != nil {
				return err
			}
		}
	}
	return nil
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}

func setupGit(repoURL, ref, targetDir string) error {
	// 1. Clone
	cmd := exec.Command("git", "clone", repoURL, targetDir)
	if out, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("git clone failed: %s (%w)", string(out), err)
	}

	// 2. Checkout ref if provided
	if ref != "" {
		cmd = exec.Command("git", "checkout", ref)
		cmd.Dir = targetDir
		if out, err := cmd.CombinedOutput(); err != nil {
			return fmt.Errorf("git checkout failed: %s (%w)", string(out), err)
		}
	}
	return nil
}

func setupZip(url, targetDir string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// Create a temp file to store the zip
	tmpFile, err := os.CreateTemp("", "tenkai-asset-*.zip")
	if err != nil {
		return err
	}
	defer os.Remove(tmpFile.Name())

	_, err = io.Copy(tmpFile, resp.Body)
	if err != nil {
		return err
	}
	tmpFile.Close()

	// Unzip
	r, err := zip.OpenReader(tmpFile.Name())
	if err != nil {
		return err
	}
	defer r.Close()

	for _, f := range r.File {
		fpath := filepath.Join(targetDir, f.Name)

		if f.FileInfo().IsDir() {
			os.MkdirAll(fpath, os.ModePerm)
			continue
		}

		if err := os.MkdirAll(filepath.Dir(fpath), os.ModePerm); err != nil {
			return err
		}

		outFile, err := os.OpenFile(fpath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
		if err != nil {
			return err
		}

		rc, err := f.Open()
		if err != nil {
			outFile.Close()
			return err
		}

		_, err = io.Copy(outFile, rc)

		outFile.Close()
		rc.Close()
	}
	return nil
}

type githubIssue struct {
	Title string `json:"title"`
	Body  string `json:"body"`
}

func fetchGithubIssue(issueURL string) (*githubIssue, error) {
	// Parse URL: https://github.com/owner/repo/issues/number
	parts := strings.Split(issueURL, "/")
	if len(parts) < 7 {
		return nil, fmt.Errorf("invalid github issue url format")
	}
	owner := parts[3]
	repo := parts[4]
	number := parts[6]

	apiURL := fmt.Sprintf("https://api.github.com/repos/%s/%s/issues/%s", owner, repo, number)
	resp, err := http.Get(apiURL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("github api returned status %d", resp.StatusCode)
	}

	var issue githubIssue
	if err := json.NewDecoder(resp.Body).Decode(&issue); err != nil {
		return nil, err
	}
	return &issue, nil
}
