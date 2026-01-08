package history

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
)

// ExperimentRecord represents a single entry in the experiment index.
type ExperimentRecord struct {
	Timestamp   string `json:"timestamp"`
	Name        string `json:"name"`
	ConfigPath  string `json:"config_path"` // Path to the used config file (original or copy)
	ResultsPath string `json:"results_path"`
	ReportPath  string `json:"report_path"`
	Status      string `json:"status"` // e.g., "completed", "failed", "running"
}

// Indexer manages the experiment index file.
type Indexer struct {
	indexPath string
	mu        sync.Mutex
}

// NewIndexer creates a new Indexer for the given root directory.
func NewIndexer(rootDir string) *Indexer {
	return &Indexer{
		indexPath: filepath.Join(rootDir, "studies", "index.json"),
	}
}

// AddEntry appends a new record to the index.
func (i *Indexer) AddEntry(record *ExperimentRecord) error {
	i.mu.Lock()
	defer i.mu.Unlock()

	// entries, err := i.loadEntries()
	// if err != nil && !os.IsNotExist(err) {
	// 	return err
	// }
	// Optimistic loading, if fails we assume empty
	entries, _ := i.loadEntries()

	entries = append(entries, *record)

	return i.saveEntries(entries)
}

// UpdateStatus updates the status of an existing entry looking it up by its results path.
func (i *Indexer) UpdateStatus(resultsPath, status string) error {
	i.mu.Lock()
	defer i.mu.Unlock()

	entries, err := i.loadEntries()
	if err != nil {
		return err
	}

	updated := false
	for idx := range entries {
		if entries[idx].ResultsPath == resultsPath {
			entries[idx].Status = status
			updated = true
			break
		}
	}

	if !updated {
		return fmt.Errorf("record with results path %s not found", resultsPath)
	}

	return i.saveEntries(entries)
}

func (i *Indexer) loadEntries() ([]ExperimentRecord, error) {
	file, err := os.Open(i.indexPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var entries []ExperimentRecord
	if err := json.NewDecoder(file).Decode(&entries); err != nil {
		return nil, err
	}
	return entries, nil
}

func (i *Indexer) saveEntries(entries []ExperimentRecord) error {
	dir := filepath.Dir(i.indexPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to ensure index dir exists: %w", err)
	}

	file, err := os.Create(i.indexPath)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(entries)
}
