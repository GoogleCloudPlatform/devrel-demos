# Hackathon Judge API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Setup a production-level Go API with Gin, Clean Architecture, and In-memory storage.

**Architecture:** Pragmatic Clean Architecture with clear separation between Domain, Repository, Service, and Handler layers. Dependency injection is handled in `main.go`.

**Tech Stack:** Go, Gin, Testify.

---

### Task 1: Project Initialization

**Files:**
- Create: `go.mod`
- Create: `.gitignore`

- [ ] **Step 1: Initialize Go module**
Run: `go mod init github.com/moficodes/hackathon-judge/backend`

- [ ] **Step 2: Install dependencies**
Run: `go get github.com/gin-gonic/gin github.com/stretchr/testify/assert`

- [ ] **Step 3: Create .gitignore**
```text
bin/
tmp/
.env
*.exe
```

- [ ] **Step 4: Commit**
```bash
git add go.mod go.sum .gitignore
git commit -m "chore: initialize go module and dependencies"
```

### Task 2: Domain Models and Interfaces

**Files:**
- Create: `internal/domain/hackathon.go`
- Create: `internal/domain/project.go`

- [ ] **Step 1: Define Hackathon and Project structs**
```go
package domain

import "time"

type Hackathon struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Title       string    `json:"title"`
	Date        time.Time `json:"date"`
	Description string    `json:"description"`
	Goal        string    `json:"goal"`
	Status      string    `json:"status"`
}

type Project struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Title       string    `json:"title"`
	URL         string    `json:"url"`
	GitHubURL   string    `json:"github_url"`
	TeamName    string    `json:"team_name"`
	Document    string    `json:"document"`
	Date        time.Time `json:"date"`
	HackathonID string    `json:"hackathon_id"`
	Score       float64   `json:"score"`
}
```

- [ ] **Step 2: Define Repository Interfaces**
```go
// Add to internal/domain/hackathon.go
type HackathonRepository interface {
	GetAll() ([]Hackathon, error)
	GetByID(id string) (Hackathon, error)
}

// Add to internal/domain/project.go
type ProjectRepository interface {
	GetByHackathonID(hackathonID string) ([]Project, error)
}
```

- [ ] **Step 3: Commit**
```bash
git add internal/domain
git commit -m "feat: define domain models and interfaces"
```

### Task 3: In-Memory Repository Implementation

**Files:**
- Create: `internal/repository/memory_repo.go`

- [ ] **Step 1: Implement In-Memory Repositories**
```go
package repository

import (
	"errors"
	"github.com/moficodes/hackathon-judge/backend/internal/domain"
)

type memoryRepo struct {
	hackathons []domain.Hackathon
	projects   []domain.Project
}

func NewMemoryRepo() *memoryRepo {
	return &memoryRepo{
		hackathons: []domain.Hackathon{
			{ID: "1", Name: "Hack1", Title: "Summer Hack", Status: "Active"},
		},
		projects: []domain.Project{
			{ID: "p1", Name: "Proj1", HackathonID: "1"},
		},
	}
}

func (r *memoryRepo) GetAll() ([]domain.Hackathon, error) {
	return r.hackathons, nil
}

func (r *memoryRepo) GetByID(id string) (domain.Hackathon, error) {
	for _, h := range r.hackathons {
		if h.ID == id {
			return h, nil
		}
	}
	return domain.Hackathon{}, errors.New("hackathon not found")
}

func (r *memoryRepo) GetByHackathonID(hackathonID string) ([]domain.Project, error) {
	var result []domain.Project
	for _, p := range r.projects {
		if p.HackathonID == hackathonID {
			result = append(result, p)
		}
	}
	return result, nil
}
```

- [ ] **Step 2: Commit**
```bash
git add internal/repository
git commit -m "feat: implement in-memory repository"
```

### Task 4: Service Layer Implementation

**Files:**
- Create: `internal/service/hackathon_service.go`

- [ ] **Step 1: Implement Hackathon Service**
```go
package service

import "github.com/moficodes/hackathon-judge/backend/internal/domain"

type HackathonService struct {
	repo        domain.HackathonRepository
	projectRepo domain.ProjectRepository
}

func NewHackathonService(repo domain.HackathonRepository, projectRepo domain.ProjectRepository) *HackathonService {
	return &HackathonService{repo: repo, projectRepo: projectRepo}
}

func (s *HackathonService) ListHackathons() ([]domain.Hackathon, error) {
	return s.repo.GetAll()
}

func (s *HackathonService) ListProjectsByHackathon(id string) ([]domain.Project, error) {
	return s.projectRepo.GetByHackathonID(id)
}
```

- [ ] **Step 2: Commit**
```bash
git add internal/service
git commit -m "feat: implement service layer"
```

### Task 5: HTTP Handlers Implementation

**Files:**
- Create: `internal/handler/hackathon_handler.go`

- [ ] **Step 1: Implement Gin Handlers**
```go
package handler

import (
	"net/http"
	"github.com/gin-gonic/gin"
	"github.com/moficodes/hackathon-judge/backend/internal/service"
)

type HackathonHandler struct {
	svc *service.HackathonService
}

func NewHackathonHandler(svc *service.HackathonService) *HackathonHandler {
	return &HackathonHandler{svc: svc}
}

func (h *HackathonHandler) RegisterRoutes(r *gin.Engine) {
	api := r.Group("/api")
	{
		api.GET("/hackathons", h.GetHackathons)
		api.GET("/hackathons/:id/projects", h.GetProjects)
	}
}

func (h *HackathonHandler) GetHackathons(c *gin.Context) {
	res, err := h.svc.ListHackathons()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, res)
}

func (h *HackathonHandler) GetProjects(c *gin.Context) {
	id := c.Param("id")
	res, err := h.svc.ListProjectsByHackathon(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, res)
}
```

- [ ] **Step 2: Commit**
```bash
git add internal/handler
git commit -m "feat: implement http handlers"
```

### Task 6: Main Application and Logging

**Files:**
- Create: `cmd/api/main.go`
- Create: `pkg/logger/logger.go`

- [ ] **Step 1: Setup Main with DI**
```go
package main

import (
	"log"
	"github.com/gin-gonic/gin"
	"github.com/moficodes/hackathon-judge/backend/internal/handler"
	"github.com/moficodes/hackathon-judge/backend/internal/repository"
	"github.com/moficodes/hackathon-judge/backend/internal/service"
)

func main() {
	r := gin.Default()

	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo)
	h := handler.NewHackathonHandler(svc)

	h.RegisterRoutes(r)

	log.Println("Server starting on :8080")
	if err := r.Run(":8080"); err != nil {
		log.Fatal(err)
	}
}
```

- [ ] **Step 2: Commit**
```bash
git add cmd/api pkg/logger
git commit -m "feat: setup main application and routing"
```

### Task 7: Verification and Testing

**Files:**
- Create: `internal/handler/hackathon_handler_test.go`

- [ ] **Step 1: Write integration test for GET /api/hackathons**
```go
package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"github.com/gin-gonic/gin"
	"github.com/moficodes/hackathon-judge/backend/internal/domain"
	"github.com/moficodes/hackathon-judge/backend/internal/repository"
	"github.com/moficodes/hackathon-judge/backend/internal/service"
	"github.com/stretchr/testify/assert"
)

func TestGetHackathons(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo)
	h := NewHackathonHandler(svc)
	h.RegisterRoutes(r)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/api/hackathons", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var res []domain.Hackathon
	json.Unmarshal(w.Body.Bytes(), &res)
	assert.Greater(t, len(res), 0)
}
```

- [ ] **Step 2: Run tests**
Run: `go test ./internal/... -v`
Expected: PASS

- [ ] **Step 3: Commit**
```bash
git add internal/handler/hackathon_handler_test.go
git commit -m "test: add integration tests for handlers"
```
