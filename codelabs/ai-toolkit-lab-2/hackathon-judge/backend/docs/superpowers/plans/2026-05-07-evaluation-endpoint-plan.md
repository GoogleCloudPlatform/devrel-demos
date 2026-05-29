# Evaluation Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a new API endpoint `GET /api/projects/:id/evaluations` to return the evaluations for a specific project.

**Architecture:** Extend the `HackathonService` to fetch evaluations from `EvaluationRepository` and add a new Gin route and handler method to `HackathonHandler`.

**Tech Stack:** Go, Gin, Testify.

---

### Task 1: Service Layer Update

**Files:**
- Modify: `internal/service/hackathon_service.go`

- [ ] **Step 1: Add `ListEvaluationsByProject` method**

```go
// Add to the service interface and implementation
func (s *hackathonService) ListEvaluationsByProject(projectID string) ([]domain.Evaluation, error) {
	return s.evalRepo.GetByProjectID(projectID)
}
```
*Note: Make sure to add this method signature to the `HackathonService` interface as well.*

- [ ] **Step 2: Commit**
```bash
git add internal/service/hackathon_service.go
git commit -m "feat: add ListEvaluationsByProject to service"
```

### Task 2: Handler Layer Update and Testing

**Files:**
- Modify: `internal/handler/hackathon_handler.go`
- Modify: `internal/handler/hackathon_handler_test.go`

- [ ] **Step 1: Implement `GetEvaluations` and register route**

```go
// Add to RegisterRoutes in internal/handler/hackathon_handler.go
// api.GET("/projects/:id/evaluations", h.GetEvaluations)

// Add handler method
func (h *HackathonHandler) GetEvaluations(c *gin.Context) {
	id := c.Param("id")
	res, err := h.svc.ListEvaluationsByProject(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, res)
}
```

- [ ] **Step 2: Write integration test for the new endpoint**

```go
// Add to internal/handler/hackathon_handler_test.go
func TestGetEvaluations(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo, repo)
	h := NewHackathonHandler(svc)
	h.RegisterRoutes(r)

	// Pre-seed an evaluation via the service
	err := svc.AddEvaluation(domain.Evaluation{
		ID: "e1", ProjectID: "p1", JudgeID: "j1", TotalScore: 9.5,
	})
	assert.NoError(t, err)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/api/projects/p1/evaluations", nil)
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var res []domain.Evaluation
	err = json.Unmarshal(w.Body.Bytes(), &res)
	assert.NoError(t, err)
	assert.Greater(t, len(res), 0)
	assert.Equal(t, "e1", res[0].ID)
}
```

- [ ] **Step 3: Run tests**
Run: `go test ./internal/handler/... -v`
Expected: PASS

- [ ] **Step 4: Commit**
```bash
git add internal/handler/hackathon_handler.go internal/handler/hackathon_handler_test.go
git commit -m "feat: add GetEvaluations endpoint and tests"
```
