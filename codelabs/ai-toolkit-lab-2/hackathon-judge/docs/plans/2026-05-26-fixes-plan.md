# Codebase Fixes: Sandbox Bug, Race Condition, & Stuck Evaluations Watchdog

**Goal:** Implement robust fixes for three critical issues in the Hackathon Judge system.

**Tech Stack:** Go (FastAPI-equivalent REST API backend), Python (Agent), Pub/Sub, Kubernetes sandboxing.

---

## Task 1: Fix shlex.quote bug in Python Sandbox Agent

**Objective:** Write raw `SANDBOX_PROMPT` to `prompt.md` rather than escaping it with `shlex.quote`.

**Files:**
- Modify: `agent/src/adapters/outbound/shared_sandbox.py:94-96`

**Step 1: Write raw prompt instead of quoted string**
```python
# Before
safe_prompt = shlex.quote(SANDBOX_PROMPT)
sandbox.files.write('prompt.md', safe_prompt)

# After
sandbox.files.write('prompt.md', SANDBOX_PROMPT)
```

**Step 2: Verification**
Confirm that the agent parses the prompt file as raw Markdown text rather than a single quoted, escaped string.

---

## Task 2: Fix Go Backend Recalculation Race Conditions

**Objective:** Prevent race conditions when retrieving evaluations, calculating project averages, and updating score columns concurrently by adding a thread-safe mutex lock.

**Files:**
- Modify: `backend/internal/service/hackathon_service.go`

**Step 1: Add a sync.Mutex to hackathonService struct**
```go
import "sync"

type hackathonService struct {
	repo        domain.HackathonRepository
	projectRepo domain.ProjectRepository
	evalRepo    domain.EvaluationRepository
	publisher   domain.TaskPublisher
	scoreMu     sync.Mutex // Guard score recalculations
}
```

**Step 2: Lock the mutex during recalculation in AddEvaluation**
```go
func (s *hackathonService) AddEvaluation(eval domain.Evaluation) error {
    // ... criteria calculation & saving evaluation ...

    s.scoreMu.Lock()
    defer s.scoreMu.Unlock()

    evals, err := s.evalRepo.GetByProjectID(eval.ProjectID)
    // ... compute average and UpdateScore ...
}
```

**Step 3: Guard calculations in TriggerJudging as well**
```go
if eval.Status == "SUCCESS" {
    s.scoreMu.Lock()
    evals, err := s.evalRepo.GetByProjectID(projectID)
    if err == nil {
        // ... compute average and UpdateScore ...
    }
    s.scoreMu.Unlock()
}
```

**Step 4: Verification**
Run Go backend unit tests to ensure they continue to pass and no concurrent execution anomalies occur.

---

## Task 3: Stuck "RUNNING" State Watchdog

**Objective:** Automatically mark evaluations stuck in `RUNNING` for more than 15 minutes as `FAILED` to prevent frontend dashboard hangs.

**Files:**
- Modify: `backend/internal/service/hackathon_service.go`

**Step 1: Implement checkStuckEvaluations and startWatchdog**
```go
func (s *hackathonService) StartWatchdog(interval time.Duration, timeout time.Duration) {
	ticker := time.NewTicker(interval)
	go func() {
		for range ticker.C {
			s.checkStuckEvaluations(timeout)
		}
	}()
}

func (s *hackathonService) checkStuckEvaluations(timeout time.Duration) {
	hackathons, err := s.repo.GetAll()
	if err != nil {
		return
	}
	for _, h := range hackathons {
		projects, err := s.projectRepo.GetByHackathonID(h.ID)
		if err != nil {
			continue
		}
		for _, p := range projects {
			evals, err := s.evalRepo.GetByProjectID(p.ID)
			if err != nil {
				continue
			}
			for _, e := range evals {
				if e.Status == "RUNNING" && time.Since(e.CreatedAt) > timeout {
					e.Status = "FAILED"
					e.Comment = fmt.Sprintf("Evaluation timed out after %v", timeout)
					_ = s.evalRepo.Update(e)
				}
			}
		}
	}
}
```

**Step 2: Initialize watchdog in NewHackathonService**
Start the watchdog automatically on service startup:
```go
func NewHackathonService(...) HackathonService {
	s := &hackathonService{...}
	s.StartWatchdog(5*time.Minute, 15*time.Minute)
	return s
}
```

**Step 3: Verification**
Confirm background execution and verify that old "RUNNING" tasks transition correctly to "FAILED".
