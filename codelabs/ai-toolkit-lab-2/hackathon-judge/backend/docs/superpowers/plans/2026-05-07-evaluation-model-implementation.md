# Evaluation Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the new `Evaluation` and `CriteriaScore` domain models and their repository interface to track multiple judge scores for a project.

**Architecture:** Add new domain entities to `internal/domain` and extend the `internal/repository/memory_repo.go` to handle storage and retrieval of these entities.

**Tech Stack:** Go, Testify.

---

### Task 1: Domain Models and Repository Interface

**Files:**
- Create: `internal/domain/evaluation.go`

- [ ] **Step 1: Define CriteriaScore and Evaluation structs**
```go
package domain

import "time"

type CriteriaScore struct {
	Name   string  `json:"name"`
	Score  float64 `json:"score"`
	Weight float64 `json:"weight"`
}

type Evaluation struct {
	ID          string          `json:"id"`
	ProjectID   string          `json:"project_id"`
	JudgeID     string          `json:"judge_id"`
	Criteria    []CriteriaScore `json:"criteria"`
	TotalScore  float64         `json:"total_score"`
	Comment     string          `json:"comment"`
	CreatedAt   time.Time       `json:"created_at"`
}

type EvaluationRepository interface {
	Save(eval Evaluation) error
	GetByProjectID(projectID string) ([]Evaluation, error)
}
```

- [ ] **Step 2: Commit**
```bash
git add internal/domain/evaluation.go
git commit -m "feat: add evaluation and criteria score domain models"
```

### Task 2: In-Memory Repository Updates

**Files:**
- Modify: `internal/repository/memory_repo.go`

- [ ] **Step 1: Update memoryRepo struct and NewMemoryRepo**
Add `evaluations` slice to `memoryRepo`.

```go
type memoryRepo struct {
	hackathons  []domain.Hackathon
	projects    []domain.Project
	evaluations []domain.Evaluation
}

func NewMemoryRepo() *memoryRepo {
	return &memoryRepo{
		hackathons: []domain.Hackathon{
			{ID: "1", Name: "Hack1", Title: "Summer Hack", Status: "Active"},
		},
		projects: []domain.Project{
			{ID: "p1", Name: "Proj1", HackathonID: "1", Score: 0},
		},
		evaluations: []domain.Evaluation{},
	}
}
```

- [ ] **Step 2: Implement EvaluationRepository methods**

```go
func (r *memoryRepo) Save(eval domain.Evaluation) error {
	r.evaluations = append(r.evaluations, eval)
	return nil
}

func (r *memoryRepo) GetByProjectID(projectID string) ([]domain.Evaluation, error) {
	var result []domain.Evaluation
	for _, e := range r.evaluations {
		if e.ProjectID == projectID {
			result = append(result, e)
		}
	}
	return result, nil
}
```

- [ ] **Step 3: Add logic to update Project average score in Save**
When an evaluation is saved, we need to update the average score of the corresponding project.

```go
func (r *memoryRepo) Save(eval domain.Evaluation) error {
	r.evaluations = append(r.evaluations, eval)
	
	// Recalculate average project score
	var total float64
	var count float64
	for _, e := range r.evaluations {
		if e.ProjectID == eval.ProjectID {
			total += e.TotalScore
			count++
		}
	}
	
	if count > 0 {
		avg := total / count
		for i, p := range r.projects {
			if p.ID == eval.ProjectID {
				r.projects[i].Score = avg
				break
			}
		}
	}

	return nil
}
```

- [ ] **Step 4: Commit**
```bash
git add internal/repository/memory_repo.go
git commit -m "feat: implement evaluation repository and project score recalculation"
```

### Task 3: Service Layer Update and Testing

**Files:**
- Modify: `internal/service/hackathon_service.go`
- Create: `internal/service/hackathon_service_test.go`

- [ ] **Step 1: Add AddEvaluation method to HackathonService**

```go
// Add to internal/service/hackathon_service.go
func (s *hackathonService) AddEvaluation(eval domain.Evaluation) error {
	// 1. Save evaluation
	if err := s.evalRepo.Save(eval); err != nil {
		return err
	}

	// 2. Get all evaluations for project to calculate average
	evals, err := s.evalRepo.GetByProjectID(eval.ProjectID)
	if err != nil {
		return err
	}

	var total float64
	for _, e := range evals {
		total += e.TotalScore
	}
	
	avg := total / float64(len(evals))

	// 3. Update project score
	return s.projectRepo.UpdateScore(eval.ProjectID, avg)
}
```
*Note: Ensure the service interface and struct have access to the `EvaluationRepository`.*

- [ ] **Step 2: Write test for Evaluation save and average calculation**

```go
package service

import (
	"testing"
	"github.com/moficodes/hackathon-judge/backend/internal/domain"
	"github.com/moficodes/hackathon-judge/backend/internal/repository"
	"github.com/stretchr/testify/assert"
)

func TestAddEvaluationUpdatesProjectScore(t *testing.T) {
	repo := repository.NewMemoryRepo()
	svc := NewHackathonService(repo, repo, repo) // Assuming repo implements all 3

	// Given a project exists (p1) with score 0
	projects, _ := repo.GetByHackathonID("1")
	assert.Equal(t, float64(0), projects[0].Score)

	// When adding first evaluation
	err := svc.AddEvaluation(domain.Evaluation{
		ID: "e1", ProjectID: "p1", JudgeID: "j1", TotalScore: 8.0,
	})
	assert.NoError(t, err)

	// Then score should be 8.0
	projects, _ = repo.GetByHackathonID("1")
	assert.Equal(t, float64(8.0), projects[0].Score)

	// When adding second evaluation
	err = svc.AddEvaluation(domain.Evaluation{
		ID: "e2", ProjectID: "p1", JudgeID: "j2", TotalScore: 6.0,
	})
	assert.NoError(t, err)

	// Then score should be average (7.0)
	projects, _ = repo.GetByHackathonID("1")
	assert.Equal(t, float64(7.0), projects[0].Score)
}
```

- [ ] **Step 3: Run tests**
Run: `go test ./internal/service/... -v`
Expected: PASS

- [ ] **Step 4: Commit**
```bash
git add internal/service/hackathon_service.go internal/service/hackathon_service_test.go
git commit -m "feat: add service logic for evaluations and tests"
```
