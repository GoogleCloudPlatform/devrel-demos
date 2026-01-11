package handlers

import (
	"net/http"
	"strconv"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
)

func (api *API) GetSummaries(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}

	// 1. Get Experiment for Control Alt
	exp, err := api.DB.GetExperimentByID(id)
	if err != nil {
		return nil, err
	}

	// 2. Get Results
	runResults, err := api.DB.GetRunResults(id, 1000000, 0) // Fetch all for summary calculation
	if err != nil {
		return nil, err
	}

	// 3. Convert
	var results []runner.Result
	for _, dr := range runResults {
		results = append(results, api.Runner.FromDBRunResult(&dr))
	}

	// 4. Calculate
	foundAlts := make(map[string]bool)
	for _, r := range results {
		foundAlts[r.Alternative] = true
	}
	var allAlts []string
	for k := range foundAlts {
		allAlts = append(allAlts, k)
	}

	summary := runner.CalculateSummary(results, exp.ExperimentControl, allAlts)

	// 5. Flatten to list
	var rows []models.ExperimentSummaryRow
	for _, row := range summary.Alternatives {
		row.ExperimentID = id
		rows = append(rows, row)
	}

	return rows, nil
}

func (api *API) GetExperimentRuns(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}

	page, _ := strconv.Atoi(r.URL.Query().Get("page"))
	if page < 1 {
		page = 1
	}
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	if limit < 1 {
		limit = 1000 // Default to high limit if not specified for backward compatibility
	}
	offset := (page - 1) * limit

	return api.DB.GetRunResults(id, limit, offset)
}

func (api *API) GetToolStats(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}
	return api.DB.GetToolStats(id)
}

func (api *API) GetRunFiles(r *http.Request) (any, error) {

	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid Run ID")
	}
	res, err := api.DB.GetRunFiles(id)
	if err != nil {
		return nil, err
	}
	if res == nil {
		return []interface{}{}, nil
	}
	return res, nil
}

func (api *API) GetRunTests(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid Run ID")
	}
	res, err := api.DB.GetTestResults(id)
	if err != nil {
		return nil, err
	}
	if res == nil {
		return []interface{}{}, nil
	}
	return res, nil
}
func (api *API) GetRunLint(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid Run ID")
	}
	res, err := api.DB.GetLintResults(id)
	if err != nil {
		return nil, err
	}
	if res == nil {
		return []interface{}{}, nil
	}
	return res, nil
}

func (api *API) GetRunTools(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid Run ID")
	}
	res, err := api.DB.GetToolUsage(id)
	if err != nil {
		return nil, err
	}
	if res == nil {
		return []interface{}{}, nil
	}
	return res, nil
}

func (api *API) GetRunMessages(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid Run ID")
	}

	page, _ := strconv.Atoi(r.URL.Query().Get("page"))
	if page < 1 {
		page = 1
	}
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	if limit < 1 {
		limit = 1000 // Default high limit
	}
	offset := (page - 1) * limit

	res, err := api.DB.GetMessages(id, limit, offset)

	if err != nil {
		return nil, err
	}
	if res == nil {
		return []interface{}{}, nil
	}
	return res, nil
}
