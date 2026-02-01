package db

import (
	"context"
	"fmt"
)

// ConfigBlock represents a reusable configuration component.
type ConfigBlock struct {
	ID      int64  `json:"id"`
	Name    string `json:"name"`
	Type    string `json:"type"` // "agent", "system_prompt", "context", "settings", "mcp_server", "extension"
	Content string `json:"content"`
}

// CreateBlock creates a new configuration block.
func (db *DB) CreateBlock(name, blockType, content string) (int64, error) {
	return db.InsertReturningID(context.Background(), "INSERT INTO config_blocks (name, type, content) VALUES (?, ?, ?)", name, blockType, content)
}

// UpdateBlock updates an existing configuration block.
func (db *DB) UpdateBlock(id int64, name, blockType, content string) error {
	_, err := db.conn.ExecContext(context.Background(), db.Rebind("UPDATE config_blocks SET name = ?, type = ?, content = ? WHERE id = ?"), name, blockType, content, id)
	if err != nil {
		return fmt.Errorf("failed to update block: %w", err)
	}
	return nil
}

// DeleteBlock deletes a configuration block by ID.
func (db *DB) DeleteBlock(id int64) error {
	_, err := db.conn.ExecContext(context.Background(), db.Rebind("DELETE FROM config_blocks WHERE id = ?"), id)
	if err != nil {
		return fmt.Errorf("failed to delete block: %w", err)
	}
	return nil
}

// GetBlock retrieves a configuration block by ID.
func (db *DB) GetBlock(id int64) (*ConfigBlock, error) {
	var b ConfigBlock
	err := db.conn.QueryRowContext(context.Background(), db.Rebind("SELECT id, name, type, content FROM config_blocks WHERE id = ?"), id).Scan(&b.ID, &b.Name, &b.Type, &b.Content)
	if err != nil {
		return nil, fmt.Errorf("failed to get block: %w", err)
	}
	return &b, nil
}

// ListBlocks retrieves all configuration blocks, optionally filtered by type.
func (db *DB) ListBlocks(blockType string) ([]ConfigBlock, error) {
	query := `SELECT id, name, type, content FROM config_blocks`
	var args []interface{}

	if blockType != "" {
		query += ` WHERE type = ?`
		args = append(args, blockType)
	}
	query += ` ORDER BY name ASC`

	rows, err := db.conn.QueryContext(context.Background(), db.Rebind(query), args...)
	if err != nil {
		return nil, fmt.Errorf("failed to list blocks: %w", err)
	}
	defer func() { _ = rows.Close() }()

	var blocks []ConfigBlock
	for rows.Next() {
		var b ConfigBlock
		if err := rows.Scan(&b.ID, &b.Name, &b.Type, &b.Content); err != nil {
			return nil, fmt.Errorf("failed to scan block: %w", err)
		}
		blocks = append(blocks, b)
	}
	return blocks, nil
}
