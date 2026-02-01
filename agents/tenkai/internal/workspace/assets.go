package workspace

import (
	"archive/zip"
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
)

// SyncAssets copies assets from the scenario config to the target directory.
func (m *Manager) SyncAssets(ctx context.Context, cfg *config.ScenarioConfig, tmplPath, targetDir string) error {
	for _, asset := range cfg.Assets {
		targetPath := filepath.Join(targetDir, asset.Target)
		if asset.Target == "." {
			targetPath = targetDir
		}

		switch asset.Type {
		case "directory":
			src := filepath.Join(tmplPath, asset.Source)
			if err := copyDir(src, targetPath); err != nil {
				return fmt.Errorf("failed to copy directory asset %s: %w", src, err)
			}
		case "file":
			// Prefer Source if available
			if asset.Source != "" {
				src := filepath.Join(tmplPath, asset.Source)
				if err := copyFile(src, targetPath); err != nil {
					return fmt.Errorf("failed to copy file asset %s: %w", src, err)
				}
			} else if asset.Content != "" {
				// Fallback to inline content
				if err := os.WriteFile(targetPath, []byte(asset.Content), 0644); err != nil {
					return fmt.Errorf("failed to write inline file asset %s: %w", targetPath, err)
				}
			}
		case "git":
			if err := setupGit(ctx, asset.Source, asset.Ref, targetPath); err != nil {
				return fmt.Errorf("failed to setup git asset %s: %w", asset.Source, err)
			}
		case "zip":
			if err := setupZip(ctx, asset.Source, targetPath); err != nil {
				return fmt.Errorf("failed to setup zip asset %s: %w", asset.Source, err)
			}
		}
	}
	return nil
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
	defer func() { _ = in.Close() }()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer func() { _ = out.Close() }()

	_, err = io.Copy(out, in)
	return err
}

func setupGit(ctx context.Context, repoURL, ref, targetDir string) error {
	// 1. Clone
	cmd := exec.CommandContext(ctx, "git", "clone", repoURL, targetDir)
	if out, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("git clone failed: %s (%w)", string(out), err)
	}

	// 2. Checkout ref if provided
	if ref != "" {
		cmd = exec.CommandContext(ctx, "git", "checkout", ref)
		cmd.Dir = targetDir
		if out, err := cmd.CombinedOutput(); err != nil {
			return fmt.Errorf("git checkout failed: %s (%w)", string(out), err)
		}
	}
	return nil
}

func setupZip(ctx context.Context, url, targetDir string) error {
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return err
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer func() { _ = resp.Body.Close() }()

	// Create a temp file to store the zip
	tmpFile, err := os.CreateTemp("", "tenkai-asset-*.zip")
	if err != nil {
		return err
	}
	defer func() {
		_ = tmpFile.Close()
		_ = os.Remove(tmpFile.Name())
	}()

	_, err = io.Copy(tmpFile, resp.Body)
	if err != nil {
		return err
	}

	// Unzip
	r, err := zip.OpenReader(tmpFile.Name())
	if err != nil {
		return err
	}
	defer func() { _ = r.Close() }()

	for _, f := range r.File {
		fpath := filepath.Join(targetDir, f.Name)

		if f.FileInfo().IsDir() {
			_ = os.MkdirAll(fpath, os.ModePerm)
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
			_ = outFile.Close()
			return err
		}

		_, err = io.Copy(outFile, rc)

		_ = outFile.Close()
		_ = rc.Close()
	}
	return nil
}
