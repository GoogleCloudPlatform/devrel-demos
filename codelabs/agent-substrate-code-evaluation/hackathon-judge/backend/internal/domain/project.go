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

package domain

import "time"

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

type ProjectRepository interface {
	GetByHackathonID(hackathonID string) ([]Project, error)
	GetProjectByID(id string) (Project, error)
	UpdateScore(projectID string, score float64) error
}
