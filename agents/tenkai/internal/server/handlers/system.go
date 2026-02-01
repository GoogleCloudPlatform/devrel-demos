package handlers

import (
	"net/http"
)

func (api *API) HandleHealth(r *http.Request) (any, error) {
	return map[string]string{"status": "ok"}, nil
}

func (api *API) HandleGlobalStats(r *http.Request) (any, error) {
	return api.DB.GetGlobalStats()
}
