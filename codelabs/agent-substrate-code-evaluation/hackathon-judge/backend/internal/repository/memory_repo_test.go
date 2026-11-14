// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package repository_test

import (
	"github.com/moficodes/hackathon-judge/backend/internal/domain"
	"github.com/moficodes/hackathon-judge/backend/internal/repository"
	"sync"
	"testing"
	"time"
)

func TestMemoryRepo_Concurrency(t *testing.T) {
	repo := repository.NewMemoryRepo()

	var wg sync.WaitGroup
	// Concurrently read and write to verify thread safety
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			repo.GetByHackathonID("1")
			repo.UpdateScore("p1", float64(i))
			repo.Save(domain.Evaluation{ProjectID: "p1", TotalScore: float64(i)})
			repo.GetAll()
			repo.GetByID("1")
			repo.GetByProjectID("p1")
		}(i)
	}
	wg.Wait()
}

func TestMemoryRepo_SaveDoesNotUpdateScore(t *testing.T) {
	repo := repository.NewMemoryRepo()

	// Ensure saving evaluation doesn't modify project score automatically anymore
	eval := domain.Evaluation{ProjectID: "p1", TotalScore: 100.0}
	repo.Save(eval)

	projects, _ := repo.GetByHackathonID("1")
	var p1 *domain.Project
	for _, p := range projects {
		if p.ID == "p1" {
			p1 = &p
			break
		}
	}

	if p1 == nil {
		t.Fatalf("project p1 not found")
	}

	// Original score was 0.0, shouldn't change to 100.0 based solely on save.
	if p1.Score != 0.0 {
		t.Errorf("Expected score to remain 0.0, got %f", p1.Score)
	}
}

func TestMemoryRepo_UpdateScore(t *testing.T) {
	repo := repository.NewMemoryRepo()

	err := repo.UpdateScore("p1", 99.5)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	projects, _ := repo.GetByHackathonID("1")
	var p1 *domain.Project
	for _, p := range projects {
		if p.ID == "p1" {
			p1 = &p
			break
		}
	}

	if p1.Score != 99.5 {
		t.Errorf("Expected score to be 99.5, got %f", p1.Score)
	}
}

func TestMemoryRepo_Update(t *testing.T) {
	repo := repository.NewMemoryRepo()
	eval := domain.Evaluation{
		ID:         "eval1",
		ProjectID:  "p1",
		JudgeID:    "j1",
		Status:     "RUNNING",
		TotalScore: 0,
		Comment:    "",
		CreatedAt:  time.Now(),
	}
	_ = repo.Save(eval)

	eval.Status = "SUCCESS"
	eval.TotalScore = 95.5
	eval.Comment = "Great job"
	
	err := repo.Update(eval)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	evals, _ := repo.GetByProjectID("p1")
	if len(evals) != 1 || evals[0].Status != "SUCCESS" || evals[0].TotalScore != 95.5 {
		t.Fatalf("update failed, got: %+v", evals)
	}
}
