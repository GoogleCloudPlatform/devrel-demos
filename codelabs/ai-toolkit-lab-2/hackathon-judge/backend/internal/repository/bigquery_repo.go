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
	"context"
	"fmt"
	"time"

	"cloud.google.com/go/bigquery"
	"github.com/moficodes/hackathon-judge/backend/internal/domain"
	"google.golang.org/api/iterator"
)

type BigQueryRepo struct {
	client    *bigquery.Client
	projectID string
	datasetID string
}

func NewBigQueryRepo(client *bigquery.Client, projectID string, datasetID string) *BigQueryRepo {
	return &BigQueryRepo{
		client:    client,
		projectID: projectID,
		datasetID: datasetID,
	}
}

type bqCriterion struct {
	ID          string  `bigquery:"id"`
	Name        string  `bigquery:"name"`
	Description string  `bigquery:"description"`
	Weight      float64 `bigquery:"weight"`
	Score       float64 `bigquery:"score"`
	MaxScore    float64 `bigquery:"max_score"`
}

type bqHackathon struct {
	ID            string        `bigquery:"id"`
	Title         string        `bigquery:"title"`
	Date          time.Time     `bigquery:"date"`
	Description   string        `bigquery:"description"`
	Goal          string        `bigquery:"goal"`
	Status        string        `bigquery:"status"`
	Criteria      []bqCriterion `bigquery:"criteria"`
	BonusCriteria []bqCriterion `bigquery:"bonus_criteria"`
}

func (r *BigQueryRepo) mapBQHackathon(bqH bqHackathon) (domain.Hackathon, error) {
	h := domain.Hackathon{
		ID:          bqH.ID,
		Title:       bqH.Title,
		Date:        bqH.Date,
		Description: bqH.Description,
		Goal:        bqH.Goal,
		Status:      bqH.Status,
	}

	h.Criteria = make([]domain.Criterion, len(bqH.Criteria))
	for i, c := range bqH.Criteria {
		h.Criteria[i] = domain.Criterion{
			Name:        c.Name,
			Weight:      c.Weight,
			Description: c.Description,
			MaxScore:    c.MaxScore,
		}
	}

	h.BonusCriteria = make([]domain.Criterion, len(bqH.BonusCriteria))
	for i, c := range bqH.BonusCriteria {
		h.BonusCriteria[i] = domain.Criterion{
			Name:        c.Name,
			Weight:      c.Weight,
			Description: c.Description,
			MaxScore:    c.MaxScore,
		}
	}
	return h, nil
}

func (r *BigQueryRepo) GetAll() ([]domain.Hackathon, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	query := r.client.Query(fmt.Sprintf("SELECT * FROM `%s.%s.hackathons`", r.projectID, r.datasetID))
	it, err := query.Read(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to read hackathons: %w", err)
	}

	var hackathons []domain.Hackathon
	for {
		var row bqHackathon
		err := it.Next(&row)
		if err == iterator.Done {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("failed to iterate hackathons: %w", err)
		}
		h, err := r.mapBQHackathon(row)
		if err != nil {
			return nil, fmt.Errorf("failed to map hackathon row: %w", err)
		}
		hackathons = append(hackathons, h)
	}
	return hackathons, nil
}

func (r *BigQueryRepo) GetByID(id string) (domain.Hackathon, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	query := r.client.Query(fmt.Sprintf("SELECT * FROM `%s.%s.hackathons` WHERE id = @id LIMIT 1", r.projectID, r.datasetID))
	query.Parameters = []bigquery.QueryParameter{
		{Name: "id", Value: id},
	}
	it, err := query.Read(ctx)
	if err != nil {
		return domain.Hackathon{}, fmt.Errorf("failed to read hackathon: %w", err)
	}

	var row bqHackathon
	err = it.Next(&row)
	if err == iterator.Done {
		return domain.Hackathon{}, fmt.Errorf("hackathon not found")
	}
	if err != nil {
		return domain.Hackathon{}, fmt.Errorf("failed to iterate hackathon: %w", err)
	}

	return r.mapBQHackathon(row)
}

type bqCriteriaScore struct {
	Name        string  `bigquery:"name"`
	Description string  `bigquery:"description"`
	Weight      float64 `bigquery:"weight"`
	Score       float64 `bigquery:"score"`
	MaxScore    float64 `bigquery:"max_score"`
}

type bqNestedEvaluation struct {
	ID         string            `bigquery:"id"`
	JudgeID    string            `bigquery:"judge_id"`
	Status     string            `bigquery:"status"`
	Criteria   []bqCriteriaScore `bigquery:"criteria"`
	TotalScore float64           `bigquery:"total_score"`
	Comment    string            `bigquery:"comment"`
	CreatedAt  time.Time         `bigquery:"created_at"`
}

type bqProject struct {
	ID          string               `bigquery:"id"`
	Name        string               `bigquery:"name"`
	Title       string               `bigquery:"title"`
	URL         string               `bigquery:"url"`
	GitHubURL   string               `bigquery:"github_url"`
	TeamName    string               `bigquery:"team_name"`
	Document    bigquery.NullString  `bigquery:"document"`
	Date        time.Time            `bigquery:"processing_date"`
	HackathonID string               `bigquery:"hackathon_id"`
	Score       float64              `bigquery:"score"`
}

func (r *BigQueryRepo) mapBQProject(bqP bqProject) domain.Project {
	doc := ""
	if bqP.Document.Valid {
		doc = bqP.Document.StringVal
	}

	return domain.Project{
		ID:          bqP.ID,
		Name:        bqP.Name,
		Title:       bqP.Title,
		URL:         bqP.URL,
		GitHubURL:   bqP.GitHubURL,
		TeamName:    bqP.TeamName,
		Document:    doc,
		Date:        bqP.Date,
		HackathonID: bqP.HackathonID,
		Score:       bqP.Score,
	}
}


func (r *BigQueryRepo) GetByHackathonID(hackathonID string) ([]domain.Project, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	query := r.client.Query(fmt.Sprintf("SELECT * FROM `%s.%s.projects` WHERE hackathon_id = @hackathon_id", r.projectID, r.datasetID))
	query.Parameters = []bigquery.QueryParameter{
		{Name: "hackathon_id", Value: hackathonID},
	}
	it, err := query.Read(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to read projects: %w", err)
	}

	var projects []domain.Project
	for {
		var row bqProject
		err := it.Next(&row)
		if err == iterator.Done {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("failed to iterate projects: %w", err)
		}
		projects = append(projects, r.mapBQProject(row))
	}
	return projects, nil
}

func (r *BigQueryRepo) GetProjectByID(id string) (domain.Project, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	query := r.client.Query(fmt.Sprintf("SELECT * FROM `%s.%s.projects` WHERE id = @id LIMIT 1", r.projectID, r.datasetID))
	query.Parameters = []bigquery.QueryParameter{
		{Name: "id", Value: id},
	}
	it, err := query.Read(ctx)
	if err != nil {
		return domain.Project{}, fmt.Errorf("failed to read project: %w", err)
	}

	var row bqProject
	err = it.Next(&row)
	if err == iterator.Done {
		return domain.Project{}, fmt.Errorf("project not found")
	}
	if err != nil {
		return domain.Project{}, fmt.Errorf("failed to iterate project: %w", err)
	}

	return r.mapBQProject(row), nil
}

func (r *BigQueryRepo) UpdateScore(projectID string, score float64) error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	query := r.client.Query(fmt.Sprintf("UPDATE `%s.%s.projects` SET score = @score WHERE id = @id", r.projectID, r.datasetID))
	query.Parameters = []bigquery.QueryParameter{
		{Name: "score", Value: score},
		{Name: "id", Value: projectID},
	}

	job, err := query.Run(ctx)
	if err != nil {
		return fmt.Errorf("failed to run update query: %w", err)
	}
	status, err := job.Wait(ctx)
	if err != nil {
		return fmt.Errorf("failed to wait for update query: %w", err)
	}
	if status.Err() != nil {
		return fmt.Errorf("update query failed: %w", status.Err())
	}
	return nil
}

type bqEvaluationRow struct {
	ProjectID  string            `bigquery:"project_id"`
	ID         string            `bigquery:"id"`
	JudgeID    string            `bigquery:"judge_id"`
	Status     string            `bigquery:"status"`
	Criteria   []bqCriteriaScore `bigquery:"criteria_json"`
	TotalScore float64           `bigquery:"total_score"`
	Comment    string            `bigquery:"comment"`
	CreatedAt  time.Time         `bigquery:"created_at"`
}

func (r *BigQueryRepo) Save(eval domain.Evaluation) error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if eval.CreatedAt.IsZero() {
		eval.CreatedAt = time.Now()
	}

	bqEval := bqNestedEvaluation{
		ID:         eval.ID,
		JudgeID:    eval.JudgeID,
		Status:     eval.Status,
		TotalScore: eval.TotalScore,
		Comment:    eval.Comment,
		CreatedAt:  eval.CreatedAt,
	}

	bqEval.Criteria = make([]bqCriteriaScore, len(eval.Criteria))
	for i, c := range eval.Criteria {
		bqEval.Criteria[i] = bqCriteriaScore{
			Name:        c.Name,
			Score:       c.Score,
			Description: c.Reasoning,
			Weight:      c.Weight,
			MaxScore:    c.MaxScore,
		}
	}

	query := r.client.Query(fmt.Sprintf("INSERT INTO `%s.%s.evaluations` (id, project_id, judge_id, status, total_score, comment, created_at, criteria_json) VALUES (@id, @project_id, @judge_id, @status, @total_score, @comment, @created_at, @criteria_json)", r.projectID, r.datasetID))
	query.Parameters = []bigquery.QueryParameter{
		{Name: "id", Value: eval.ID},
		{Name: "project_id", Value: eval.ProjectID},
		{Name: "judge_id", Value: eval.JudgeID},
		{Name: "status", Value: eval.Status},
		{Name: "total_score", Value: eval.TotalScore},
		{Name: "comment", Value: eval.Comment},
		{Name: "created_at", Value: eval.CreatedAt},
		{Name: "criteria_json", Value: bqEval.Criteria},
	}

	job, err := query.Run(ctx)
	if err != nil {
		return fmt.Errorf("failed to run insert (append) query: %w", err)
	}
	status, err := job.Wait(ctx)
	if err != nil {
		return fmt.Errorf("failed to wait for insert (append) query: %w", err)
	}
	if status.Err() != nil {
		return fmt.Errorf("insert (append) query failed: %w", status.Err())
	}
	return nil
}

func (r *BigQueryRepo) Update(eval domain.Evaluation) error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	bqEval := bqNestedEvaluation{
		ID:         eval.ID,
		JudgeID:    eval.JudgeID,
		Status:     eval.Status,
		TotalScore: eval.TotalScore,
		Comment:    eval.Comment,
		CreatedAt:  eval.CreatedAt,
	}

	bqEval.Criteria = make([]bqCriteriaScore, len(eval.Criteria))
	for i, c := range eval.Criteria {
		bqEval.Criteria[i] = bqCriteriaScore{
			Name:        c.Name,
			Score:       c.Score,
			Description: c.Reasoning,
			Weight:      c.Weight,
			MaxScore:    c.MaxScore,
		}
	}

	query := r.client.Query(fmt.Sprintf(`
		UPDATE `+"`"+`%s.%s.evaluations`+"`"+` 
		SET status = @status, 
		    total_score = @total_score, 
		    comment = @comment, 
		    criteria_json = @criteria_json 
		WHERE id = @id`, r.projectID, r.datasetID))

	query.Parameters = []bigquery.QueryParameter{
		{Name: "status", Value: eval.Status},
		{Name: "total_score", Value: eval.TotalScore},
		{Name: "comment", Value: eval.Comment},
		{Name: "criteria_json", Value: bqEval.Criteria},
		{Name: "id", Value: eval.ID},
	}

	job, err := query.Run(ctx)
	if err != nil {
		return fmt.Errorf("failed to run update query: %w", err)
	}
	status, err := job.Wait(ctx)
	if err != nil {
		return fmt.Errorf("failed to wait for update query: %w", err)
	}
	if status.Err() != nil {
		return fmt.Errorf("update query failed: %w", status.Err())
	}
	return nil
}

func (r *BigQueryRepo) GetEvaluationByID(id string) (domain.Evaluation, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	query := r.client.Query(fmt.Sprintf("SELECT id, project_id, judge_id, status, total_score, comment, created_at, criteria_json FROM `%s.%s.evaluations` WHERE id = @id LIMIT 1", r.projectID, r.datasetID))
	query.Parameters = []bigquery.QueryParameter{
		{Name: "id", Value: id},
	}

	it, err := query.Read(ctx)
	if err != nil {
		return domain.Evaluation{}, fmt.Errorf("failed to read evaluation: %w", err)
	}

	var row bqEvaluationRow
	err = it.Next(&row)
	if err == iterator.Done {
		return domain.Evaluation{}, fmt.Errorf("evaluation not found")
	}
	if err != nil {
		return domain.Evaluation{}, fmt.Errorf("failed to iterate evaluation: %w", err)
	}

	criteria := make([]domain.CriteriaScore, len(row.Criteria))
	for i, c := range row.Criteria {
		criteria[i] = domain.CriteriaScore{
			Name:      c.Name,
			Score:     c.Score,
			Reasoning: c.Description,
			MaxScore:  c.MaxScore,
			Weight:    c.Weight,
		}
	}

	return domain.Evaluation{
		ID:         row.ID,
		ProjectID:  row.ProjectID,
		JudgeID:    row.JudgeID,
		Status:     row.Status,
		TotalScore: row.TotalScore,
		Comment:    row.Comment,
		CreatedAt:  row.CreatedAt,
		Criteria:   criteria,
	}, nil
}

func (r *BigQueryRepo) GetByProjectID(projectID string) ([]domain.Evaluation, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	query := r.client.Query(fmt.Sprintf("SELECT id, project_id, judge_id, status, total_score, comment, created_at, criteria_json FROM `%s.%s.evaluations` WHERE project_id = @project_id ORDER BY created_at DESC", r.projectID, r.datasetID))
	query.Parameters = []bigquery.QueryParameter{
		{Name: "project_id", Value: projectID},
	}

	it, err := query.Read(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to query evaluations: %w", err)
	}

	var evaluations []domain.Evaluation
	for {
		var row bqEvaluationRow
		err = it.Next(&row)
		if err == iterator.Done {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("failed to iterate evaluations: %w", err)
		}

		criteria := make([]domain.CriteriaScore, len(row.Criteria))
		for i, c := range row.Criteria {
			criteria[i] = domain.CriteriaScore{
				Name:      c.Name,
				Score:     c.Score,
				Reasoning: c.Description,
				MaxScore:  c.MaxScore,
				Weight:    c.Weight,
			}
		}

		evaluations = append(evaluations, domain.Evaluation{
			ID:         row.ID,
			ProjectID:  row.ProjectID,
			JudgeID:    row.JudgeID,
			Status:     row.Status,
			TotalScore: row.TotalScore,
			Comment:    row.Comment,
			CreatedAt:  row.CreatedAt,
			Criteria:   criteria,
		})
	}

	return evaluations, nil
}

func (r *BigQueryRepo) Create(hackathon domain.Hackathon) error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	bqCriteria := make([]bqCriterion, len(hackathon.Criteria))
	for i, c := range hackathon.Criteria {
		bqCriteria[i] = bqCriterion{
			ID:          fmt.Sprintf("crit_%d", i),
			Name:        c.Name,
			Description: c.Description,
			Weight:      c.Weight,
			Score:       0,
			MaxScore:    c.MaxScore,
		}
	}

	bqBonusCriteria := make([]bqCriterion, len(hackathon.BonusCriteria))
	for i, c := range hackathon.BonusCriteria {
		bqBonusCriteria[i] = bqCriterion{
			ID:          fmt.Sprintf("bonus_%d", i),
			Name:        c.Name,
			Description: c.Description,
			Weight:      c.Weight,
			Score:       0,
			MaxScore:    c.MaxScore,
		}
	}

	query := r.client.Query(fmt.Sprintf(`
		INSERT INTO `+"`"+`%s.%s.hackathons`+"`"+` (id, title, date, description, goal, status, criteria, bonus_criteria) 
		VALUES (@id, @title, @date, @description, @goal, @status, @criteria, @bonus_criteria)`, r.projectID, r.datasetID))

	query.Parameters = []bigquery.QueryParameter{
		{Name: "id", Value: hackathon.ID},
		{Name: "title", Value: hackathon.Title},
		{Name: "date", Value: hackathon.Date},
		{Name: "description", Value: hackathon.Description},
		{Name: "goal", Value: hackathon.Goal},
		{Name: "status", Value: hackathon.Status},
		{Name: "criteria", Value: bqCriteria},
		{Name: "bonus_criteria", Value: bqBonusCriteria},
	}

	job, err := query.Run(ctx)
	if err != nil {
		return fmt.Errorf("failed to run insert query for hackathon: %w", err)
	}
	status, err := job.Wait(ctx)
	if err != nil {
		return fmt.Errorf("failed to wait for insert query for hackathon: %w", err)
	}
	if status.Err() != nil {
		return fmt.Errorf("insert query failed for hackathon: %w", status.Err())
	}
	return nil
}

func (r *BigQueryRepo) CreateProject(project domain.Project) error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	query := r.client.Query(fmt.Sprintf(`
		INSERT INTO `+"`"+`%s.%s.projects`+"`"+` (id, name, title, url, readme_ref, github_url, team_name, document, processing_date, hackathon_id, score) 
		VALUES (@id, @name, @title, @url, NULL, @github_url, @team_name, @document, @processing_date, @hackathon_id, @score)`, r.projectID, r.datasetID))

	query.Parameters = []bigquery.QueryParameter{
		{Name: "id", Value: project.ID},
		{Name: "name", Value: project.Name},
		{Name: "title", Value: project.Title},
		{Name: "url", Value: project.URL},
		{Name: "github_url", Value: project.GitHubURL},
		{Name: "team_name", Value: project.TeamName},
		{Name: "document", Value: project.Document},
		{Name: "processing_date", Value: project.Date},
		{Name: "hackathon_id", Value: project.HackathonID},
		{Name: "score", Value: project.Score},
	}

	job, err := query.Run(ctx)
	if err != nil {
		return fmt.Errorf("failed to run insert query for project: %w", err)
	}
	status, err := job.Wait(ctx)
	if err != nil {
		return fmt.Errorf("failed to wait for insert query for project: %w", err)
	}
	if status.Err() != nil {
		return fmt.Errorf("insert query failed for project: %w", status.Err())
	}
	return nil
}

func (r *BigQueryRepo) Delete(id string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	query := r.client.Query(fmt.Sprintf(`
		DELETE FROM `+"`"+`%s.%s.hackathons`+"`"+` WHERE id = @id`, r.projectID, r.datasetID))

	query.Parameters = []bigquery.QueryParameter{
		{Name: "id", Value: id},
	}

	job, err := query.Run(ctx)
	if err != nil {
		return fmt.Errorf("failed to run delete query for hackathon: %w", err)
	}
	status, err := job.Wait(ctx)
	if err != nil {
		return fmt.Errorf("failed to wait for delete query for hackathon: %w", err)
	}
	if status.Err() != nil {
		return fmt.Errorf("delete query failed for hackathon: %w", status.Err())
	}
	return nil
}

