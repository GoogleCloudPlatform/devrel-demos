package server

func (s *Server) registerRoutes() {
	// Health
	s.router.HandleFunc("GET /api/health", s.api.Wrap(s.api.HandleHealth))
	s.router.HandleFunc("GET /api/stats", s.api.Wrap(s.api.HandleGlobalStats))

	// Experiments
	s.router.HandleFunc("GET /api/experiments", s.api.Wrap(s.api.ListExperiments))
	s.router.HandleFunc("DELETE /api/experiments", s.api.Wrap(s.api.DeleteAllExperiments))
	s.router.HandleFunc("POST /api/experiments/run", s.api.Wrap(s.api.StartExperiment))

	s.router.HandleFunc("GET /api/experiments/{id}", s.api.Wrap(s.api.GetExperiment))
	s.router.HandleFunc("POST /api/experiments/{id}/analysis", s.api.Wrap(s.api.SaveAIAnalysis))
	s.router.HandleFunc("POST /api/experiments/{id}/annotations", s.api.Wrap(s.api.SaveExperimentAnnotations))
	s.router.HandleFunc("DELETE /api/experiments/{id}", s.api.Wrap(s.api.DeleteExperiment))

	s.router.HandleFunc("GET /api/experiments/{id}/summaries", s.api.Wrap(s.api.GetSummaries))
	s.router.HandleFunc("GET /api/experiments/{id}/runs", s.api.Wrap(s.api.GetExperimentRuns))
	s.router.HandleFunc("GET /api/experiments/{id}/tool-stats", s.api.Wrap(s.api.GetToolStats))
	s.router.HandleFunc("POST /api/experiments/{id}/control", s.api.Wrap(s.api.ControlExperiment))
	s.router.HandleFunc("POST /api/experiments/{id}/relaunch", s.api.Wrap(s.api.RelaunchExperiment))
	s.router.HandleFunc("POST /api/experiments/{id}/lock", s.api.Wrap(s.api.HandleExperimentLock))
	s.router.HandleFunc("GET /api/experiments/{id}/export", s.api.HandleExportReport) // No Wrap!

	// Logs
	s.router.HandleFunc("GET /api/logs", s.api.Wrap(s.api.HandleLogs))

	// Runs (Sub-resources)
	s.router.HandleFunc("GET /api/runs/{id}/files", s.api.Wrap(s.api.GetRunFiles))
	s.router.HandleFunc("GET /api/runs/{id}/tests", s.api.Wrap(s.api.GetRunTests))
	s.router.HandleFunc("GET /api/runs/{id}/lint", s.api.Wrap(s.api.GetRunLint))
	s.router.HandleFunc("GET /api/runs/{id}/tools", s.api.Wrap(s.api.GetRunTools))
	s.router.HandleFunc("GET /api/runs/{id}/messages", s.api.Wrap(s.api.GetRunMessages))
	s.router.HandleFunc("POST /api/runs/{id}/reval", s.api.Wrap(s.api.ReEvaluateRun))
	s.router.HandleFunc("POST /api/experiments/{id}/reval", s.api.Wrap(s.api.ReEvaluateExperiment))

	// Jobs
	s.router.HandleFunc("GET /api/jobs/{id}", s.api.Wrap(s.api.GetJob))

	// Scenarios
	s.router.HandleFunc("GET /api/scenarios", s.api.Wrap(s.api.ListScenarios))
	s.router.HandleFunc("POST /api/scenarios", s.api.Wrap(s.api.CreateScenario))
	s.router.HandleFunc("GET /api/scenarios/{id}", s.api.Wrap(s.api.GetScenario))
	s.router.HandleFunc("PUT /api/scenarios/{id}", s.api.Wrap(s.api.UpdateScenario))
	s.router.HandleFunc("DELETE /api/scenarios/{id}", s.api.Wrap(s.api.DeleteScenario))
	s.router.HandleFunc("POST /api/scenarios/{id}/lock", s.api.Wrap(s.api.HandleScenarioLock))

	// Templates
	s.router.HandleFunc("GET /api/templates", s.api.Wrap(s.api.ListTemplates))
	s.router.HandleFunc("POST /api/templates", s.api.Wrap(s.api.CreateTemplate))
	s.router.HandleFunc("DELETE /api/templates", s.api.Wrap(s.api.DeleteAllTemplates))
	s.router.HandleFunc("DELETE /api/templates/delete-all", s.api.Wrap(s.api.DeleteAllTemplates)) // Alias used by frontend

	s.router.HandleFunc("GET /api/templates/{id}/config", s.api.Wrap(s.api.GetTemplateConfig))
	s.router.HandleFunc("POST /api/templates/{id}/config", s.api.Wrap(s.api.UpdateTemplate))
	s.router.HandleFunc("PUT /api/templates/{id}/config", s.api.Wrap(s.api.UpdateTemplate)) // Idiomatic PUT
	s.router.HandleFunc("DELETE /api/templates/{id}", s.api.Wrap(s.api.DeleteTemplate))
	s.router.HandleFunc("POST /api/templates/{id}/lock", s.api.Wrap(s.api.HandleTemplateLock))
}
