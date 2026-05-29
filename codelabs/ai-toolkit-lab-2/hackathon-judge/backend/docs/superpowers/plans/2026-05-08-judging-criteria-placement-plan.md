# Judging Criteria Placement Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the definition of judging criteria from individual evaluations to the Hackathon level, and update the scoring logic to reflect this.

**Architecture:** Domain-driven refactor. Updates to structs in the domain layer, followed by updating mock data in the repository, updating the TotalScore calculation in the service layer, and fixing existing tests.

**Tech Stack:** Go

---

### Task 1: Update Domain Models

**Files:**
- Modify: `internal/domain/hackathon.go`
- Modify: `internal/domain/evaluation.go`

- [ ] **Step 1: Add Criterion to hackathon.go**

```go
type Criterion struct {
	Name        string  `json:"name"`
	Weight      float64 `json:"weight"`
	Description string  `json:"description"`
}
```

- [ ] **Step 2: Add Criteria field to Hackathon struct in hackathon.go**

```go
type Hackathon struct {
	ID          string      `json:"id"`
	Name        string      `json:"name"`
	Title       string      `json:"title"`
	Date        time.Time   `json:"date"`
	Description string      `json:"description"`
	Goal        string      `json:"goal"`
	Status      string      `json:"status"`
	Criteria    []Criterion `json:"criteria"`
}
```

- [ ] **Step 3: Update CriteriaScore struct in evaluation.go**

```go
type CriteriaScore struct {
	Name      string  `json:"name"`
	Score     float64 `json:"score"`
	Reasoning string  `json:"reasoning"`
}
```

- [ ] **Step 4: Run tests to ensure they fail (expected)**

Run: `go test ./...`
Expected: FAIL due to compilation errors related to `Weight` missing from `CriteriaScore`.

- [ ] **Step 5: Commit**

```bash
git add internal/domain/hackathon.go internal/domain/evaluation.go
git commit -m "feat: move criteria definitions from evaluation to hackathon"
```

### Task 2: Update Repository Data

**Files:**
- Modify: `internal/repository/memory_repo.go`

- [ ] **Step 1: Update Hackathon mock data in memory_repo.go**

Add `Criteria` to the mock `Hackathon`:

```go
		hackathons: []domain.Hackathon{
			{
				ID:     "1",
				Name:   "Hack1",
				Title:  "Summer Hack",
				Status: "Active",
				Criteria: []domain.Criterion{
					{Name: "Technology", Weight: 2, Description: "1-barely works, 5-really good tested"},
					{Name: "Design", Weight: 1, Description: "1-ugly, 5-beautiful"},
				},
			},
		},
```

- [ ] **Step 2: Commit**

```bash
git add internal/repository/memory_repo.go
git commit -m "chore: update repository mock data with criteria"
```

### Task 3: Update Service Logic

**Files:**
- Modify: `internal/service/hackathon_service.go`
- Modify: `internal/domain/project.go`
- Modify: `internal/repository/memory_repo.go`

- [ ] **Step 1: Add GetByID to ProjectRepository in project.go**

Modify `internal/domain/project.go` to add `GetByID` to the interface:

```go
type ProjectRepository interface {
	GetByHackathonID(hackathonID string) ([]Project, error)
	GetByID(id string) (Project, error)
	UpdateScore(projectID string, score float64) error
}
```

- [ ] **Step 2: Implement GetByID for projects in memory_repo.go**

At the bottom of `internal/repository/memory_repo.go`:

```go
func (r *memoryRepo) GetByID(id string) (domain.Project, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	for _, p := range r.projects {
		if p.ID == id {
			return p, nil
		}
	}
	return domain.Project{}, errors.New("project not found")
}
```

- [ ] **Step 3: Update AddEvaluation method in hackathon_service.go**

Calculate `eval.TotalScore` before saving. We need to fetch the Hackathon via the Project.

```go
func (s *hackathonService) AddEvaluation(eval domain.Evaluation) error {
	// Fetch Project to get HackathonID
	project, err := s.projectRepo.GetByID(eval.ProjectID)
	if err != nil {
		return err
	}

	// Fetch Hackathon to get weights
	hackathon, err := s.repo.GetByID(project.HackathonID)
	if err != nil {
		return err
	}

	// Calculate TotalScore
	var evalTotal float64
	for _, cs := range eval.Criteria {
		weight := 0.0
		for _, hc := range hackathon.Criteria {
			if hc.Name == cs.Name {
				weight = hc.Weight
				break
			}
		}
		evalTotal += cs.Score * weight
	}
	eval.TotalScore = evalTotal

	if err := s.evalRepo.Save(eval); err != nil {
		return err
	}

	evals, err := s.evalRepo.GetByProjectID(eval.ProjectID)
	if err != nil {
		return err
	}

	var total float64
	for _, e := range evals {
		total += e.TotalScore
	}
	average := total / float64(len(evals))

	return s.projectRepo.UpdateScore(eval.ProjectID, average)
}
```

- [ ] **Step 4: Commit**

```bash
git add internal/service/hackathon_service.go internal/domain/project.go internal/repository/memory_repo.go
git commit -m "feat: implement dynamic criteria scoring in service"
```

### Task 4: Fix Tests

**Files:**
- Modify: `internal/service/hackathon_service_test.go`
- Modify: `internal/handler/hackathon_handler_test.go`

- [ ] **Step 1: Fix hackathon_service_test.go**

Remove `Weight` from test instantiations of `CriteriaScore`. Add `Reasoning` if desired, or omit it. `TotalScore` is now calculated dynamically. Update the test expectations around `expectedTotal`.

```go
// ... inside TestHackathonService_AddEvaluation ...
	eval1 := domain.Evaluation{
		ProjectID: "p1",
		Criteria: []domain.CriteriaScore{
			{Name: "Technology", Score: 4}, // Weight is 2 from mock data
			{Name: "Design", Score: 5},     // Weight is 1 from mock data
		},
	}
	// Total for eval1 = (4 * 2) + (5 * 1) = 13

	eval2 := domain.Evaluation{
		ProjectID: "p1",
		Criteria: []domain.CriteriaScore{
			{Name: "Technology", Score: 2}, // Weight 2 -> 4
			{Name: "Design", Score: 3},     // Weight 1 -> 3
		},
	}
	// Total for eval2 = 7

	// Average = (13 + 7) / 2 = 10
// Update expected values in the test to match 10
```

- [ ] **Step 2: Fix hackathon_handler_test.go**

Remove `Weight` from test instantiations of `CriteriaScore`. Update expected scores if necessary based on the mock data weights.

```go
// ... inside TestListEvaluationsByProject ...
	err := svc.AddEvaluation(domain.Evaluation{
		ProjectID: "p1",
		Criteria: []domain.CriteriaScore{
			{Name: "Technology", Score: 4}, // 8
			{Name: "Design", Score: 5},     // 5 -> 13
		},
	})
```

- [ ] **Step 3: Run all tests to verify**

Run: `go test ./...`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add internal/service/hackathon_service_test.go internal/handler/hackathon_handler_test.go
git commit -m "test: fix tests after criteria refactor"
```
