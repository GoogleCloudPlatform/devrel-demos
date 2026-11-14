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

package service_test

import (
	"testing"
	"time"

	"github.com/moficodes/hackathon-judge/backend/internal/domain"
	"github.com/moficodes/hackathon-judge/backend/internal/repository"
	"github.com/moficodes/hackathon-judge/backend/internal/service"
	"github.com/stretchr/testify/assert"
)

func TestGetHackathon(t *testing.T) {
	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo, repo, nil)

	h, err := svc.GetHackathon("1")
	assert.NoError(t, err)
	assert.Equal(t, "1", h.ID)
	assert.Equal(t, "Summer Hack", h.Title)

	_, err = svc.GetHackathon("invalid")
	assert.Error(t, err)
}

func TestGetProject(t *testing.T) {
	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo, repo, nil)

	p, err := svc.GetProject("p1")
	assert.NoError(t, err)
	assert.Equal(t, "p1", p.ID)
	assert.Equal(t, "Proj1", p.Name)

	_, err = svc.GetProject("invalid")
	assert.Error(t, err)
}

func TestAddEvaluationUpdatesProjectScore(t *testing.T) {
	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo, repo, nil)

	// memoryRepo initializes a project with ID "p1" under hackathon "1"
	eval1 := domain.Evaluation{
		ID:        "e1",
		ProjectID: "p1",
		Criteria: []domain.CriteriaScore{
			{Name: "Innovation & Originality", Score: 4}, // Weight is 0.2 from mock data -> 0.8
			{Name: "Technical Execution", Score: 5},      // Weight is 0.25 from mock data -> 1.25
		},
	}

	err := svc.AddEvaluation(eval1)
	assert.NoError(t, err)

	projects, err := svc.ListProjectsByHackathon("1")
	assert.NoError(t, err)
	assert.Len(t, projects, 1)
	assert.Equal(t, 2.05, projects[0].Score) // (4*0.2) + (5*0.25) = 0.8 + 1.25 = 2.05

	eval2 := domain.Evaluation{
		ID:        "e2",
		ProjectID: "p1",
		Criteria: []domain.CriteriaScore{
			{Name: "Innovation & Originality", Score: 2}, // Weight 0.2 -> 0.4
			{Name: "Technical Execution", Score: 3},      // Weight 0.25 -> 0.75
			{Name: "Clean Code", Score: 2},               // Bonus: Weight 2 -> 4.0
		},
	}

	err = svc.AddEvaluation(eval2)
	assert.NoError(t, err)

	projects, err = svc.ListProjectsByHackathon("1")
	assert.NoError(t, err)
	assert.Len(t, projects, 1)
	assert.InDelta(t, 3.6, projects[0].Score, 0.0001) // (2.05 + 5.15) / 2 = 7.2 / 2 = 3.6
}

func TestCheckStuckEvaluations(t *testing.T) {
	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo, repo, nil)

	stuckEval := domain.Evaluation{
		ID:        "stuck-1",
		ProjectID: "p1",
		JudgeID:   "sandbox",
		Status:    "RUNNING",
		CreatedAt: time.Now().Add(-20 * time.Minute),
	}
	err := repo.Save(stuckEval)
	assert.NoError(t, err)

	recentEval := domain.Evaluation{
		ID:        "recent-1",
		ProjectID: "p1",
		JudgeID:   "sandbox",
		Status:    "RUNNING",
		CreatedAt: time.Now().Add(-5 * time.Minute),
	}
	err = repo.Save(recentEval)
	assert.NoError(t, err)

	successEval := domain.Evaluation{
		ID:        "done-1",
		ProjectID: "p1",
		JudgeID:   "sandbox",
		Status:    "SUCCESS",
		CreatedAt: time.Now().Add(-30 * time.Minute),
	}
	err = repo.Save(successEval)
	assert.NoError(t, err)

	service.CheckStuckEvaluationsForTest(svc, 15*time.Minute)

	e, err := repo.GetEvaluationByID("stuck-1")
	assert.NoError(t, err)
	assert.Equal(t, "FAILED", e.Status)
	assert.Equal(t, "Evaluation timed out after 15 minutes", e.Comment)

	e, err = repo.GetEvaluationByID("recent-1")
	assert.NoError(t, err)
	assert.Equal(t, "RUNNING", e.Status)

	e, err = repo.GetEvaluationByID("done-1")
	assert.NoError(t, err)
	assert.Equal(t, "SUCCESS", e.Status)
}

func TestAddEvaluationPersistsWeightAndMaxScore(t *testing.T) {
	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo, repo, nil)

	err := svc.AddEvaluation(domain.Evaluation{
		ID:        "e-weights",
		ProjectID: "p1",
		Criteria: []domain.CriteriaScore{
			{Name: "Technical Execution", Score: 4}, // standard: weight 0.25, max 5
			{Name: "Clean Code", Score: 1},          // bonus: weight 2, max 2
			{Name: "Not A Criterion", Score: 3},     // unknown: weight 0, max 0
		},
	})
	assert.NoError(t, err)

	e, err := repo.GetEvaluationByID("e-weights")
	assert.NoError(t, err)
	assert.Equal(t, 0.25, e.Criteria[0].Weight)
	assert.Equal(t, 5.0, e.Criteria[0].MaxScore)
	assert.Equal(t, 2.0, e.Criteria[1].Weight)
	assert.Equal(t, 2.0, e.Criteria[1].MaxScore)
	assert.Equal(t, 0.0, e.Criteria[2].Weight)
	assert.Equal(t, 0.0, e.Criteria[2].MaxScore)
}

func saveRunningEval(t *testing.T, repo interface{ Save(domain.Evaluation) error }, id string) {
	t.Helper()
	assert.NoError(t, repo.Save(domain.Evaluation{
		ID: id, ProjectID: "p1", JudgeID: "sandbox", Status: "RUNNING", CreatedAt: time.Now(),
	}))
}

func TestSaveJudgingResultSuccessUpdatesEvaluationAndProjectScore(t *testing.T) {
	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo, repo, nil)
	saveRunningEval(t, repo, "tsk_1")

	err := svc.SaveJudgingResult(domain.JudgingResult{
		TaskID: "tsk_1",
		Status: "success",
		Scores: []domain.CriteriaScore{
			{Name: "Innovation & Originality", Score: 4, Weight: 0.2},
			{Name: "Technical Execution", Score: 5, Weight: 0.25},
		},
		OverallComments: "Solid work",
	})
	assert.NoError(t, err)

	e, err := repo.GetEvaluationByID("tsk_1")
	assert.NoError(t, err)
	assert.Equal(t, "SUCCESS", e.Status)
	assert.Equal(t, "Solid work", e.Comment)
	assert.Len(t, e.Criteria, 2)
	assert.InDelta(t, 2.05, e.TotalScore, 0.0001)

	p, err := svc.GetProject("p1")
	assert.NoError(t, err)
	assert.InDelta(t, 2.05, p.Score, 0.0001)
}

func TestSaveJudgingResultAveragesOnlySuccessfulEvaluations(t *testing.T) {
	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo, repo, nil)
	saveRunningEval(t, repo, "tsk_a")
	saveRunningEval(t, repo, "tsk_b")
	saveRunningEval(t, repo, "tsk_still_running")

	assert.NoError(t, svc.SaveJudgingResult(domain.JudgingResult{
		TaskID: "tsk_a", Status: "success",
		Scores: []domain.CriteriaScore{{Name: "Technical Execution", Score: 4, Weight: 0.25}},
	}))
	assert.NoError(t, svc.SaveJudgingResult(domain.JudgingResult{
		TaskID: "tsk_b", Status: "success",
		Scores: []domain.CriteriaScore{{Name: "Technical Execution", Score: 2, Weight: 0.25}},
	}))

	p, err := svc.GetProject("p1")
	assert.NoError(t, err)
	assert.InDelta(t, 0.75, p.Score, 0.0001) // (1.0 + 0.5) / 2, RUNNING eval ignored
}

func TestSaveJudgingResultErrorMarksFailed(t *testing.T) {
	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo, repo, nil)
	saveRunningEval(t, repo, "tsk_err")
	msg := "git clone failed"

	err := svc.SaveJudgingResult(domain.JudgingResult{TaskID: "tsk_err", Status: "error", ErrorMessage: &msg})
	assert.NoError(t, err)

	e, err := repo.GetEvaluationByID("tsk_err")
	assert.NoError(t, err)
	assert.Equal(t, "FAILED", e.Status)
	assert.Equal(t, "git clone failed", e.Comment)

	p, err := svc.GetProject("p1")
	assert.NoError(t, err)
	assert.Equal(t, 0.0, p.Score)
}

func TestSaveJudgingResultUnknownTask(t *testing.T) {
	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo, repo, nil)

	err := svc.SaveJudgingResult(domain.JudgingResult{TaskID: "tsk_missing", Status: "success"})
	assert.ErrorContains(t, err, "tsk_missing")
}
