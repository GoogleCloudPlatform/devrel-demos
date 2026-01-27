package handlers

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
)

// ListBlocks handles GET /api/blocks.
func (s *API) ListBlocks(r *http.Request) (any, error) {
	blockType := r.URL.Query().Get("type")
	blocks, err := s.DB.ListBlocks(blockType)
	if err != nil {
		return nil, err
	}
	return blocks, nil
}

// GetBlock handles GET /api/blocks/{id}.
func (s *API) GetBlock(r *http.Request) (any, error) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid block ID: %w", err)
	}

	block, err := s.DB.GetBlock(id)
	if err != nil {
		return nil, err
	}
	return block, nil
}

// CreateBlock handles POST /api/blocks.
func (s *API) CreateBlock(r *http.Request) (any, error) {
	var input struct {
		Name    string `json:"name"`
		Type    string `json:"type"`
		Content string `json:"content"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		return nil, fmt.Errorf("invalid request body: %w", err)
	}

	if input.Name == "" || input.Type == "" {
		return nil, fmt.Errorf("name and type are required")
	}

	id, err := s.DB.CreateBlock(input.Name, input.Type, input.Content)
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"id":      id,
		"message": "Block created successfully",
	}, nil
}

// UpdateBlock handles PUT /api/blocks/{id}.
func (s *API) UpdateBlock(r *http.Request) (any, error) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid block ID: %w", err)
	}

	var input struct {
		Name    string `json:"name"`
		Type    string `json:"type"`
		Content string `json:"content"`
	}
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		return nil, fmt.Errorf("invalid request body: %w", err)
	}

	if err := s.DB.UpdateBlock(id, input.Name, input.Type, input.Content); err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"message": "Block updated successfully",
	}, nil
}

// DeleteBlock handles DELETE /api/blocks/{id}.
func (s *API) DeleteBlock(r *http.Request) (any, error) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid block ID: %w", err)
	}

	if err := s.DB.DeleteBlock(id); err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"message": "Block deleted successfully",
	}, nil
}
