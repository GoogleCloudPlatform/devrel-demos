package handlers

import (
	"net/http"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/jobs"
)

func (api *API) GetJob(r *http.Request) (any, error) {
	id := r.PathValue("id")
	if id == "" {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid Job ID")
	}

	job := jobs.GetManager().GetJob(id)
	if job == nil {
		return nil, NewAPIError(http.StatusNotFound, "Job not found")
	}

	return job, nil
}
