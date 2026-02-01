package storage

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"cloud.google.com/go/storage"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"google.golang.org/api/iterator"
)

// Storage defines the interface for storing and retrieving run artifacts.
type Storage interface {
	Upload(ctx context.Context, runID int64, path string, content []byte) (string, error)
	Read(ctx context.Context, uri string) ([]byte, error)
	DownloadRunArtifacts(ctx context.Context, runID int64, destPath string) error
}

// GCSStorage implements ArtifactStorage using Google Cloud Storage.
type GCSStorage struct {
	client *storage.Client
	bucket string
	prefix string
}

func NewGCSStorage(ctx context.Context, bucket string, prefix string) (*GCSStorage, error) {
	client, err := storage.NewClient(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to create GCS client: %w", err)
	}
	return &GCSStorage{
		client: client,
		bucket: bucket,
		prefix: prefix,
	}, nil
}

func (s *GCSStorage) Upload(ctx context.Context, runID int64, path string, content []byte) (string, error) {
	// Object name: <prefix>/runs/<runID>/<path>
	// Path might contain subdirectories, we preserve them.
	// If path is absolute, we trim the leading slash and drive letter/volume if any to make it relative.
	// Simplifying assumption: path is relative to workspace root or handled by caller to be a clean key.

	// Clean path to remove .. and ./
	cleanPath := filepath.Clean(path)
	// Avoid leading slashes for GCS keys
	if cleanPath[0] == '/' || cleanPath[0] == '\\' {
		cleanPath = cleanPath[1:]
	}

	objectName := fmt.Sprintf("runs/%d/%s", runID, cleanPath)
	if s.prefix != "" {
		objectName = fmt.Sprintf("%s/%s", s.prefix, objectName)
	}

	wc := s.client.Bucket(s.bucket).Object(objectName).NewWriter(ctx)
	if _, err := wc.Write(content); err != nil {
		return "", fmt.Errorf("failed to write object %s: %w", objectName, err)
	}
	if err := wc.Close(); err != nil {
		return "", fmt.Errorf("failed to close writer for %s: %w", objectName, err)
	}

	return fmt.Sprintf("gs://%s/%s", s.bucket, objectName), nil
}

func (s *GCSStorage) Read(ctx context.Context, uri string) ([]byte, error) {
	// Expected URI: gs://<bucket>/<object>
	// Just minimal parsing for now or assume URI is valid gs://
	// For now, let's assume we read by Object Name directly if we knew it?
	// Or we parse the gs:// URI.

	// If URI doesn't start with gs://, assume it's a blob.
	// Actually, Read might not be needed by the runner except for caching.
	// Report viewer might need signed URLs.

	// For simplicity, let's implement basic read assuming full gs:// URI match.

	// ...
	return nil, fmt.Errorf("not implemented")
}

// DBStorage implements ArtifactStorage using the database (fallback).
type DBStorage struct {
	db *db.DB
}

func (s *GCSStorage) DownloadRunArtifacts(ctx context.Context, runID int64, destPath string) error {
	// Prefix: runs/<runID>/
	prefix := fmt.Sprintf("runs/%d/", runID)
	if s.prefix != "" {
		prefix = fmt.Sprintf("%s/%s", s.prefix, prefix)
	}

	it := s.client.Bucket(s.bucket).Objects(ctx, &storage.Query{
		Prefix: prefix,
	})

	for {
		attrs, err := it.Next()
		if err == iterator.Done {
			break
		}
		if err != nil {
			return fmt.Errorf("failed to list objects: %w", err)
		}

		// Rel path: remove prefix
		relPath := strings.TrimPrefix(attrs.Name, prefix)
		// Local path
		localPath := filepath.Join(destPath, relPath)

		if err := os.MkdirAll(filepath.Dir(localPath), 0755); err != nil {
			return err
		}

		// Download
		rc, err := s.client.Bucket(s.bucket).Object(attrs.Name).NewReader(ctx)
		if err != nil {
			return fmt.Errorf("failed to read object %s: %w", attrs.Name, err)
		}

		// Use a closure to ensure Close is called for each file
		err = func() error {
			defer rc.Close()
			data, err := io.ReadAll(rc)
			if err != nil {
				return fmt.Errorf("failed to download object %s: %w", attrs.Name, err)
			}
			if err := os.WriteFile(localPath, data, 0644); err != nil {
				return fmt.Errorf("failed to write file %s: %w", localPath, err)
			}
			return nil
		}()
		if err != nil {
			return err
		}
	}
	return nil
}

func NewDBStorage(database *db.DB) *DBStorage {
	return &DBStorage{db: database}
}

func (s *DBStorage) Upload(ctx context.Context, runID int64, path string, content []byte) (string, error) {
	f := &models.RunFile{
		RunID:       runID,
		Path:        path,
		Content:     string(content), // DB currently stores as string
		IsGenerated: true,            // Default assumption for uploads via storage
	}
	if err := s.db.SaveRunFile(f); err != nil {
		return "", err
	}
	return fmt.Sprintf("db://runs/%d/files/%s", runID, path), nil
}

func (s *DBStorage) Read(ctx context.Context, uri string) ([]byte, error) {
	// Reading from DB by arbitrary URI is tricky without ID.
	// We'll leave this for now as mostly run_files are accessed via runID queries.
	return nil, fmt.Errorf("not implemented")
}

func (s *DBStorage) DownloadRunArtifacts(ctx context.Context, runID int64, destPath string) error {
	// For DB storage, we would query run_files table
	// But currently run_files stores only explicit files, not full workspace.
	// So we can only restore what we saved.
	return fmt.Errorf("DBStorage download not implemented yet")
}
