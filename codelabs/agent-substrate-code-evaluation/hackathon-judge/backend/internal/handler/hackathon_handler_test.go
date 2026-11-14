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

package handler_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/moficodes/hackathon-judge/backend/internal/domain"
	"github.com/moficodes/hackathon-judge/backend/internal/handler"
	"github.com/moficodes/hackathon-judge/backend/internal/repository"
	"github.com/moficodes/hackathon-judge/backend/internal/service"
	"github.com/stretchr/testify/assert"
)

func setupRouter() (*gin.Engine, service.HackathonService) {
	gin.SetMode(gin.TestMode)
	r := gin.Default()
	repo := repository.NewMemoryRepo()
	svc := service.NewHackathonService(repo, repo, repo, nil)
	h := handler.NewHackathonHandler(svc)
	h.RegisterRoutes(r)
	return r, svc
}

func TestListHackathons(t *testing.T) {
	r, _ := setupRouter()

	req, _ := http.NewRequest(http.MethodGet, "/api/hackathons", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var res []domain.Hackathon
	err := json.Unmarshal(w.Body.Bytes(), &res)
	assert.NoError(t, err)
	assert.GreaterOrEqual(t, len(res), 1)
	assert.Equal(t, "Summer Hack", res[0].Title)
}

func TestListProjectsByHackathon(t *testing.T) {
	r, _ := setupRouter()

	req, _ := http.NewRequest(http.MethodGet, "/api/hackathons/1/projects", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var res []domain.Project
	err := json.Unmarshal(w.Body.Bytes(), &res)
	assert.NoError(t, err)
	assert.GreaterOrEqual(t, len(res), 1)
	assert.Equal(t, "p1", res[0].ID)
}

func TestListEvaluationsByProject(t *testing.T) {
	r, svc := setupRouter()

	// Pre-seed an evaluation via the service
	err := svc.AddEvaluation(domain.Evaluation{
		ID: "e1", ProjectID: "p1", JudgeID: "j1",
		Criteria: []domain.CriteriaScore{
			{Name: "Innovation & Originality", Score: 4}, // 0.8
			{Name: "Technical Execution", Score: 5},      // 1.25 -> 2.05
		},
	})
	assert.NoError(t, err)

	req, _ := http.NewRequest(http.MethodGet, "/api/projects/p1/evaluations", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var res []domain.Evaluation
	err = json.Unmarshal(w.Body.Bytes(), &res)
	assert.NoError(t, err)
	assert.Len(t, res, 1)
	assert.Equal(t, "e1", res[0].ID)
	assert.Equal(t, 2.05, res[0].TotalScore)
}

func TestListEvaluationsByProject_Empty(t *testing.T) {
	r, _ := setupRouter()

	req, _ := http.NewRequest(http.MethodGet, "/api/projects/p1/evaluations", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "[]", w.Body.String())
}

func TestListEvaluationsByProject_NotFound(t *testing.T) {
	r, _ := setupRouter()

	req, _ := http.NewRequest(http.MethodGet, "/api/projects/nonexistent/evaluations", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestGetHackathon(t *testing.T) {
	r, _ := setupRouter()

	req, _ := http.NewRequest(http.MethodGet, "/api/hackathons/1", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var res domain.Hackathon
	err := json.Unmarshal(w.Body.Bytes(), &res)
	assert.NoError(t, err)
	assert.Equal(t, "1", res.ID)
	assert.Equal(t, "Summer Hack", res.Title)
}

func TestGetHackathon_NotFound(t *testing.T) {
	r, _ := setupRouter()

	req, _ := http.NewRequest(http.MethodGet, "/api/hackathons/invalid_id", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestGetProject(t *testing.T) {
	r, _ := setupRouter()

	req, _ := http.NewRequest(http.MethodGet, "/api/projects/p1", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var res domain.Project
	err := json.Unmarshal(w.Body.Bytes(), &res)
	assert.NoError(t, err)
	assert.Equal(t, "p1", res.ID)
	assert.Equal(t, "Proj1", res.Name)
}

func TestGetProject_NotFound(t *testing.T) {
	r, _ := setupRouter()

	req, _ := http.NewRequest(http.MethodGet, "/api/projects/invalid_id", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}
