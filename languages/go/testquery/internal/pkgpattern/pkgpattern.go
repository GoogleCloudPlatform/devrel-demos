package pkgpattern

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os/exec"
)

// ListPackages returns a list of packages matching the given specifier.
func ListPackages(specifier string) ([]string, error) {
	args := []string{"list", "-json"}
	if specifier != "" {
		args = append(args, specifier)
	}

	cmd := exec.Command("go", args...)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("failed to list packages: %w, stderr: %s", err, stderr.String())
	}

	var packages []string
	decoder := json.NewDecoder(&stdout)
	for decoder.More() {
		var pkg struct {
			Dir string
		}
		if err := decoder.Decode(&pkg); err != nil {
			return nil, fmt.Errorf("failed to decode package json: %w", err)
		}
		packages = append(packages, pkg.Dir)
	}

	return packages, nil
}
