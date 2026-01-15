package graph

import (
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
	"golang.org/x/tools/go/packages"
)

// Watcher monitors the filesystem for changes and triggers invalidation.
type Watcher struct {
	watcher *fsnotify.Watcher
	done    chan struct{}
	wg      sync.WaitGroup
	manager *Manager

	// Debounce buffer
	eventsMu sync.Mutex
	events   map[string]time.Time // path -> lastEventTime
}

// NewWatcher creates a new watcher for the given manager.
func NewWatcher(m *Manager) (*Watcher, error) {
	fw, err := fsnotify.NewWatcher()
	if err != nil {
		return nil, err
	}
	return &Watcher{
		watcher: fw,
		done:    make(chan struct{}),
		manager: m,
		events:  make(map[string]time.Time),
	}, nil
}

// Start begins watching the root directory recursively.
func (w *Watcher) Start(root string) error {
	// Add root and all subdirectories
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil // Skip errors
		}
		if info.IsDir() {
			// Skip hidden dirs and vendor
			name := info.Name()
			if name != "." && (strings.HasPrefix(name, ".") || name == "vendor") {
				return filepath.SkipDir
			}
			return w.watcher.Add(path)
		}
		return nil
	})
	if err != nil {
		return err
	}

	w.wg.Add(1)
	go w.eventLoop()
	return nil
}

// Close stops the watcher and waits for the event loop to exit.
func (w *Watcher) Close() error {
	return w.watcher.Close()
}

func (w *Watcher) eventLoop() {
	defer w.wg.Done()

	ticker := time.NewTicker(100 * time.Millisecond) // Check buffer freq
	defer ticker.Stop()

	for {
		select {
		case event, ok := <-w.watcher.Events:
			if !ok {
				return
			}
			w.handleEvent(event)

		case err, ok := <-w.watcher.Errors:
			if !ok {
				return
			}
			log.Printf("Watcher error: %v", err)

		case <-ticker.C:
			w.processDebouncedEvents()

		case <-w.done:
			return
		}
	}
}

func (w *Watcher) handleEvent(event fsnotify.Event) {
	// We only care about .go files
	if !strings.HasSuffix(event.Name, ".go") {
		return
	}

	// Add to debounce buffer
	w.eventsMu.Lock()
	w.events[event.Name] = time.Now()
	w.eventsMu.Unlock()
}

func (w *Watcher) processDebouncedEvents() {
	w.eventsMu.Lock()
	defer w.eventsMu.Unlock()

	threshold := time.Now().Add(-500 * time.Millisecond)
	processed := make(map[string]bool)

	for path, t := range w.events {
		if t.Before(threshold) {
			// Event is "stable" enough to process
			dir := filepath.Dir(path)
			if !processed[dir] {
				// We reload the PACKAGE that contains this file.
				// Since we map packages by path, usually dir == package path (for simple layouts)
				// But simpler: just trigger Invalidate on the directory.
				go func(d string) {
					// We need to reload just this package.
					// Manager.Load will handle caching logic.
					// Force reload by invalidating cache first?
					w.manager.Invalidate(d)
				}(dir)
				processed[dir] = true
			}
			delete(w.events, path)
		}
	}
}

// Invalidate removes a package from the manager's cache and reloads it.
func (m *Manager) Invalidate(dir string) {
	// We check which cached package has files in this dir.
	m.mu.Lock()
	var pathsToReload []string
	for _, state := range m.Packages {
		// Check if any source file is in this dir
		for _, f := range state.Pkg.GoFiles {
			if filepath.Dir(f) == dir {
				delete(m.Packages, state.Pkg.PkgPath)
				pathsToReload = append(pathsToReload, dir)
				break
			}
		}
	}
	m.mu.Unlock()

	// Reload them in background
	for _, d := range pathsToReload {
		log.Printf("[Watcher] Reloading package in %s", d)
		// Load with a dummy pattern to force refresh
		cfg := &packages.Config{
			Mode: packages.NeedName | packages.NeedFiles | packages.NeedCompiledGoFiles |
				packages.NeedImports | packages.NeedDeps | packages.NeedTypes |
				packages.NeedSyntax | packages.NeedTypesInfo,
			Dir: d,
		}
		pkgs, err := packages.Load(cfg, ".")
		if err == nil {
			m.mu.Lock()
			for _, p := range pkgs {
				m.Packages[p.PkgPath] = &PackageState{
					Pkg:        p,
					LastLoaded: time.Now(),
				}
			}
			m.mu.Unlock()
		}
	}
}
