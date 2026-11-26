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
	"errors"
	"sync"

	"github.com/moficodes/hackathon-judge/backend/internal/domain"
)

type memoryRepo struct {
	mu          sync.RWMutex
	hackathons  []domain.Hackathon
	projects    []domain.Project
	evaluations []domain.Evaluation
}

func NewMemoryRepo() *memoryRepo {
	return &memoryRepo{
		hackathons: []domain.Hackathon{
			{
				ID:     "1",
				Title:  "Summer Hack",
				Status: "Active",
				Criteria: []domain.Criterion{
					{Name: "Innovation & Originality", Weight: 0.2, Description: "How unique and original is the productivity tool?\n\n**Low (1-2):** The project is essentially a \"Hello World\" of productivity (e.g., a basic CRUD to-do list with no unique features).\n**High (4-5):** The team identified a unique bottleneck—like \"context switching\" or \"decision fatigue\"—and built a tool specifically to kill that problem.", MaxScore: 5},
					{Name: "Theme Alignment (Impact)", Weight: 0.25, Description: "Does the app actually save time or remove friction?\n\n**Low (1-2):** The app might be cool, but it doesn't actually make the user more efficient.\n**High (4-5):** Does the app actually save time? Does it remove friction? A 5/5 project makes the judges want to start using the app immediately for their own work.", MaxScore: 5},
					{Name: "Technical Execution", Weight: 0.25, Description: "Quality of implementation and technical complexity.\n\n**Low (1-2):** Code is messy, or the \"app\" is just a series of static HTML pages with no logic.\n**High (4-5):** The team integrated complex elements (e.g., AI APIs, browser extensions, real-time sync, or advanced data visualization) successfully within the hackathon timeframe.", MaxScore: 5},
					{Name: "User Experience (UX/UI)", Weight: 0.2, Description: "Design for focus, minimal distractions, and clear feedback.\n\n**Low (1-2):** Buttons don't work, text is unreadable, or the workflow is frustrating.\n**High (4-5):** For productivity tools, **less is more**. Points are awarded for \"Flow State\" design—minimal distractions, keyboard shortcuts, and clear feedback.", MaxScore: 5},
					{Name: "Pitch & Demo", Weight: 0.1, Description: "Quality of the presentation and live demonstration.\n\n**Low (1-2):** The team spent too much time on the technical stack and forgot to show the actual product.\n**High (4-5):** The team clearly demonstrated a \"use case.\" They showed exactly how a user's life is better after using their tool.", MaxScore: 5},
				},
				BonusCriteria: []domain.Criterion{
					{Name: "Clean Code", Weight: 2, Description: "Repository is well-documented with a clear README.", MaxScore: 2},
					{Name: "Accessibility", Weight: 1, Description: "Project considers screen readers, high contrast, or keyboard-only navigation.", MaxScore: 1},
					{Name: "Wow Factor", Weight: 2, Description: "A specific feature that made the judges say \"Wait, how did they build that in 24 hours?\"", MaxScore: 2},
				},
			},
		},
		projects: []domain.Project{
			{ID: "p1", Name: "Proj1", HackathonID: "1", Score: 0},
		},
		evaluations: []domain.Evaluation{},
	}
}

func (r *memoryRepo) GetAll() ([]domain.Hackathon, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return append([]domain.Hackathon(nil), r.hackathons...), nil
}

func (r *memoryRepo) GetByID(id string) (domain.Hackathon, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	for _, h := range r.hackathons {
		if h.ID == id {
			return h, nil
		}
	}
	return domain.Hackathon{}, errors.New("hackathon not found")
}

func (r *memoryRepo) GetByHackathonID(hackathonID string) ([]domain.Project, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	var result []domain.Project
	for _, p := range r.projects {
		if p.HackathonID == hackathonID {
			result = append(result, p)
		}
	}
	return result, nil
}

func (r *memoryRepo) Save(eval domain.Evaluation) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.evaluations = append(r.evaluations, eval)
	return nil
}

func (r *memoryRepo) GetByProjectID(projectID string) ([]domain.Evaluation, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	var result []domain.Evaluation
	for _, e := range r.evaluations {
		if e.ProjectID == projectID {
			result = append(result, e)
		}
	}
	return result, nil
}

func (r *memoryRepo) GetEvaluationByID(id string) (domain.Evaluation, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	for _, e := range r.evaluations {
		if e.ID == id {
			return e, nil
		}
	}
	return domain.Evaluation{}, errors.New("evaluation not found")
}

func (r *memoryRepo) Update(eval domain.Evaluation) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	for i, e := range r.evaluations {
		if e.ID == eval.ID {
			r.evaluations[i] = eval
			return nil
		}
	}
	return errors.New("evaluation not found")
}

func (r *memoryRepo) UpdateScore(projectID string, score float64) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	for i, p := range r.projects {
		if p.ID == projectID {
			r.projects[i].Score = score
			return nil
		}
	}
	return errors.New("project not found")
}

func (r *memoryRepo) GetProjectByID(id string) (domain.Project, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	for _, p := range r.projects {
		if p.ID == id {
			return p, nil
		}
	}
	return domain.Project{}, errors.New("project not found")
}

func (r *memoryRepo) Create(hackathon domain.Hackathon) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.hackathons = append(r.hackathons, hackathon)
	return nil
}

func (r *memoryRepo) CreateProject(project domain.Project) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.projects = append(r.projects, project)
	return nil
}

func (r *memoryRepo) Delete(id string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	for i, h := range r.hackathons {
		if h.ID == id {
			r.hackathons = append(r.hackathons[:i], r.hackathons[i+1:]...)
			return nil
		}
	}
	return errors.New("hackathon not found")
}

