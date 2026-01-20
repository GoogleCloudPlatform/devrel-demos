package roots

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// State manages the registered project roots.
type State struct {
	mu    sync.RWMutex
	roots []string
}

// Global is the singleton instance for the entire application.
var Global = &State{}

// Add adds a new project root after normalizing it to an absolute path.
func (s *State) Add(path string) {
	abs, err := filepath.Abs(path)
	if err != nil {
		abs = path
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	for _, r := range s.roots {
		if r == abs {
			return
		}
	}
	s.roots = append(s.roots, abs)
}

// Get returns a copy of the currently registered roots.
func (s *State) Get() []string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	roots := make([]string, len(s.roots))
	copy(roots, s.roots)
	return roots
}

// Sync synchronizes roots with the MCP client.
func (s *State) Sync(ctx context.Context, session *mcp.ServerSession) {
	if session == nil {
		s.Add(".")
		return
	}

	res, err := session.ListRoots(ctx, &mcp.ListRootsParams{})
	if err != nil {
		fmt.Fprintf(os.Stderr, "Warning: failed to list roots from client: %v. Falling back to CWD.\n", err)
		s.Add(".")
		return
	}

	var rts []string
	for _, r := range res.Roots {
		if strings.HasPrefix(r.URI, "file://") {
			path := strings.TrimPrefix(r.URI, "file://")
			abs, err := filepath.Abs(path)
			if err == nil {
				rts = append(rts, abs)
			}
		}
	}

	if len(rts) == 0 {
		abs, _ := filepath.Abs(".")
		rts = append(rts, abs)
	}

	s.mu.Lock()
	s.roots = rts
	s.mu.Unlock()
}

// Validate checks if the given path is within any of the registered roots.
// It returns the absolute path if valid, or an error if not.
func (s *State) Validate(path string) (string, error) {
	if path == "" || path == "." {
		roots := s.Get()
		if len(roots) > 0 {
			return roots[0], nil
		}
		abs, _ := filepath.Abs(".")
		return abs, nil
	}

	absPath, err := filepath.Abs(path)
	if err != nil {
		return "", fmt.Errorf("invalid path: %w", err)
	}

	roots := s.Get()

	// Allow access to system temporary directory
	rawTemp := os.TempDir()
	if strings.HasPrefix(absPath, rawTemp) {
		return absPath, nil
	}
	if tempDir, err := filepath.EvalSymlinks(rawTemp); err == nil {
		// handle /var/folders/ vs /tmp mismatch on macOS
		if strings.HasPrefix(absPath, tempDir) || strings.HasPrefix(absPath, "/tmp") {
			return absPath, nil
		}
	}

	// If no roots are registered, default to CWD
	if len(roots) == 0 {
		cwd, _ := filepath.Abs(".")
		if strings.HasPrefix(absPath, cwd) {
			return absPath, nil
		}
		return "", fmt.Errorf("access denied: path %s is outside the current working directory", path)
	}

	for _, root := range roots {
		if strings.HasPrefix(absPath, root) {
			return absPath, nil
		}
	}

	return "", fmt.Errorf("access denied: path %s is outside of registered workspace roots", path)
}
