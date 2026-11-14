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

package repository

import (
	"testing"
	"time"

	"cloud.google.com/go/bigquery"
)

func TestMapBQHackathon(t *testing.T) {
	repo := &BigQueryRepo{} // We only need the method, not a real client

	date := time.Now()
	bqh := bqHackathon{
		ID:          "h1",
		Title:       "Hackathon 1",
		Date:        date,
		Description: "Desc",
		Goal:        "Goal",
		Status:      "ACTIVE",
		Criteria: []bqCriterion{
			{Name: "C1", Description: "D1", Weight: 0.5, MaxScore: 10},
		},
		BonusCriteria: []bqCriterion{
			{Name: "B1", Description: "BD1", Weight: 0.1, MaxScore: 5},
		},
	}

	h, err := repo.mapBQHackathon(bqh)

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if h.ID != "h1" || h.Title != "Hackathon 1" || h.Description != "Desc" || h.Goal != "Goal" || h.Status != "ACTIVE" || !h.Date.Equal(date) {
		t.Errorf("basic fields mapped incorrectly. got: %+v", h)
	}

	if len(h.Criteria) != 1 || h.Criteria[0].Name != "C1" || h.Criteria[0].Weight != 0.5 || h.Criteria[0].MaxScore != 10 {
		t.Errorf("criteria mapped incorrectly. got: %+v", h.Criteria)
	}

	if len(h.BonusCriteria) != 1 || h.BonusCriteria[0].Name != "B1" || h.BonusCriteria[0].Weight != 0.1 || h.BonusCriteria[0].MaxScore != 5 {
		t.Errorf("bonus criteria mapped incorrectly. got: %+v", h.BonusCriteria)
	}
}

func TestMapBQProject(t *testing.T) {
	repo := &BigQueryRepo{}
	date := time.Now()

	tests := []struct {
		name     string
		bqP      bqProject
		expected string
	}{
		{
			name: "valid document",
			bqP: bqProject{
				ID:          "p1",
				Name:        "Project 1",
				Title:       "Title 1",
				URL:         "url",
				GitHubURL:   "gh",
				TeamName:    "Team",
				Document:    bigquery.NullString{StringVal: "doc content", Valid: true},
				Date:        date,
				HackathonID: "h1",
				Score:       95.5,
			},
			expected: "doc content",
		},
		{
			name: "invalid document",
			bqP: bqProject{
				ID:          "p2",
				Name:        "Project 2",
				Title:       "Title 2",
				URL:         "url2",
				GitHubURL:   "gh2",
				TeamName:    "Team2",
				Document:    bigquery.NullString{Valid: false},
				Date:        date,
				HackathonID: "h2",
				Score:       80.0,
			},
			expected: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			p := repo.mapBQProject(tt.bqP)

			if p.ID != tt.bqP.ID || p.Name != tt.bqP.Name || p.Title != tt.bqP.Title || p.URL != tt.bqP.URL || p.GitHubURL != tt.bqP.GitHubURL || p.TeamName != tt.bqP.TeamName || p.HackathonID != tt.bqP.HackathonID || p.Score != tt.bqP.Score {
				t.Errorf("basic fields mapped incorrectly. got: %+v", p)
			}

			if p.Document != tt.expected {
				t.Errorf("document mapped incorrectly. expected: %s, got: %s", tt.expected, p.Document)
			}

			if !p.Date.Equal(tt.bqP.Date) {
				t.Errorf("date mapped incorrectly. expected: %v, got: %v", tt.bqP.Date, p.Date)
			}
		})
	}
}
