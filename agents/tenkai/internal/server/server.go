package server

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"

	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
	"gopkg.in/yaml.v3"
)

type Server struct {
	db     *db.DB
	runner *runner.Runner
	wsMgr  *workspace.Manager
	router *http.ServeMux
}
type ControlRequest struct {
	Command string `json:"command"` // "stop"
}

type StartExperimentRequest struct {
	Name         string   `json:"name"`
	TemplateID   string   `json:"template_id"`
	Reps         int      `json:"reps"`
	Concurrent   int      `json:"concurrent"`
	Control      string   `json:"control"`
	Timeout      string   `json:"timeout"`
	Alternatives []string `json:"alternatives"`
	Scenarios    []string `json:"scenarios"`
}

// APIError represents a structured error response
type APIError struct {
	Status  int    `json:"-"`
	Message string `json:"error"`
}

func (e *APIError) Error() string {
	return e.Message
}

func NewAPIError(status int, msg string) *APIError {
	return &APIError{Status: status, Message: msg}
}

// APIHandler is a function that returns data or an error
type APIHandler func(r *http.Request) (any, error)

func New(database *db.DB, r *runner.Runner, ws *workspace.Manager) *Server {
	s := &Server{
		db:     database,
		runner: r,
		wsMgr:  ws,
		router: http.NewServeMux(),
	}
	s.registerRoutes()
	return s
}

func (s *Server) Start(port int) error {
	addr := fmt.Sprintf(":%d", port)
	log.Printf("[Server] Listening on http://localhost%s", addr)

	// Chain middlewares: CORS -> Recovery -> Logger -> API Wrapper (implicit in handlers)
	// Actually, wrap the router itself with global middlewares
	handler := s.corsMiddleware(s.loggerMiddleware(s.router))

	return http.ListenAndServe(addr, handler)
}

// Middleware: CORS
func (s *Server) corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// Middleware: Logger & Recovery
func (s *Server) loggerMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if err := recover(); err != nil {
				log.Printf("Panic: %v", err)
				http.Error(w, `{"error": "Internal Server Error"}`, http.StatusInternalServerError)
			}
		}()
		// TODO: Add request logging if needed, for now standard lib logs errors
		next.ServeHTTP(w, r)
	})
}

// wrap converts an APIHandler into an http.HandlerFunc with standardized JSON responses
func (s *Server) wrap(h APIHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		data, err := h(r)
		if err != nil {
			status := http.StatusInternalServerError
			msg := err.Error()

			if apiErr, ok := err.(*APIError); ok {
				status = apiErr.Status
			} else if strings.Contains(msg, "not found") {
				status = http.StatusNotFound
			}

			log.Printf("[API Error] %s %s: %v", r.Method, r.URL.Path, err)

			w.WriteHeader(status)
			json.NewEncoder(w).Encode(map[string]string{"error": msg})
			return
		}

		if data == nil {
			// Go's json encoder handles nil interface as "null"
		}

		w.WriteHeader(http.StatusOK)
		if err := json.NewEncoder(w).Encode(data); err != nil {
			log.Printf("Failed to encode response: %v", err)
		}
	}
}

func (s *Server) registerRoutes() {
	// Health
	s.router.HandleFunc("GET /api/health", s.wrap(s.handleHealth))
	s.router.HandleFunc("GET /api/stats", s.wrap(s.handleGlobalStats))

	// Experiments
	s.router.HandleFunc("GET /api/experiments", s.wrap(s.listExperiments))
	s.router.HandleFunc("DELETE /api/experiments", s.wrap(s.deleteAllExperiments))
	s.router.HandleFunc("POST /api/experiments/run", s.wrap(s.startExperiment))

	s.router.HandleFunc("GET /api/experiments/{id}", s.wrap(s.getExperiment))
	s.router.HandleFunc("POST /api/experiments/{id}/analysis", s.wrap(s.saveAIAnalysis))
	s.router.HandleFunc("DELETE /api/experiments/{id}", s.wrap(s.deleteExperiment))

	s.router.HandleFunc("GET /api/experiments/{id}/summaries", s.wrap(s.getSummaries))
	s.router.HandleFunc("GET /api/experiments/{id}/runs", s.wrap(s.getExperimentRuns))
	s.router.HandleFunc("GET /api/experiments/{id}/tool-stats", s.wrap(s.getToolStats))
	s.router.HandleFunc("POST /api/experiments/{id}/control", s.wrap(s.controlExperiment))
	s.router.HandleFunc("POST /api/experiments/control", s.wrap(s.legacyControlExperiment))
	s.router.HandleFunc("POST /api/experiments/{id}/relaunch", s.wrap(s.relaunchExperiment))
	s.router.HandleFunc("GET /api/experiments/{id}/export", s.handleExportReport)

	// Logs
	s.router.HandleFunc("GET /api/logs", s.wrap(s.handleLogs))

	// Runs (Sub-resources)
	s.router.HandleFunc("GET /api/runs/{id}/files", s.wrap(s.getRunFiles))
	s.router.HandleFunc("GET /api/runs/{id}/tests", s.wrap(s.getRunTests))
	s.router.HandleFunc("GET /api/runs/{id}/lint", s.wrap(s.getRunLint))
	s.router.HandleFunc("GET /api/runs/{id}/tools", s.wrap(s.getRunTools))
	s.router.HandleFunc("GET /api/runs/{id}/messages", s.wrap(s.getRunMessages))

	// Scenarios
	s.router.HandleFunc("GET /api/scenarios", s.wrap(s.listScenarios))
	s.router.HandleFunc("POST /api/scenarios", s.wrap(s.createScenario))
	s.router.HandleFunc("GET /api/scenarios/{id}", s.wrap(s.getScenario))
	s.router.HandleFunc("PUT /api/scenarios/{id}", s.wrap(s.updateScenario))
	s.router.HandleFunc("DELETE /api/scenarios/{id}", s.wrap(s.deleteScenario))

	// Templates
	s.router.HandleFunc("GET /api/templates", s.wrap(s.listTemplates))
	s.router.HandleFunc("POST /api/templates", s.wrap(s.createTemplate))
	s.router.HandleFunc("DELETE /api/templates", s.wrap(s.deleteAllTemplates))
	s.router.HandleFunc("DELETE /api/templates/delete-all", s.wrap(s.deleteAllTemplates)) // Alias used by frontend

	s.router.HandleFunc("GET /api/templates/{id}/config", s.wrap(s.getTemplateConfig))
	s.router.HandleFunc("POST /api/templates/{id}/config", s.wrap(s.updateTemplate))
	s.router.HandleFunc("PUT /api/templates/{id}/config", s.wrap(s.updateTemplate)) // Idiomatic PUT
	s.router.HandleFunc("DELETE /api/templates/{id}", s.wrap(s.deleteTemplate))
}

// --- Handlers ---
func (s *Server) handleHealth(r *http.Request) (any, error) {
	return map[string]string{"status": "ok"}, nil
}

func (s *Server) handleGlobalStats(r *http.Request) (any, error) {
	return s.db.GetGlobalStats()
}

func (s *Server) listExperiments(r *http.Request) (any, error) {

	return s.db.GetExperiments()
}

func (s *Server) deleteAllExperiments(r *http.Request) (any, error) {
	if err := s.db.DeleteAllExperiments(); err != nil {
		return nil, err
	}
	return map[string]string{"message": "All experiments deleted"}, nil
}

func (s *Server) getExperiment(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}
	return s.db.GetExperimentByID(id)
}

func (s *Server) deleteExperiment(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}
	if err := s.db.DeleteExperiment(id); err != nil {
		return nil, err
	}
	return map[string]string{"message": "Experiment deleted"}, nil
}

func (s *Server) getSummaries(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}

	// 1. Get Experiment for Control Alt
	exp, err := s.db.GetExperimentByID(id)
	if err != nil {
		return nil, err
	}

	// 2. Get Results
	runResults, err := s.db.GetRunResults(id)
	if err != nil {
		return nil, err
	}

	// 3. Convert
	var results []runner.Result
	for _, dr := range runResults {
		results = append(results, s.runner.FromDBRunResult(dr))
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
	var rows []db.ExperimentSummaryRow
	for _, row := range summary.Alternatives {
		row.ExperimentID = id
		rows = append(rows, row)
	}

	return rows, nil
}

func (s *Server) getExperimentRuns(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}
	return s.db.GetRunResults(id)
}

func (s *Server) getToolStats(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}
	return s.db.GetToolStats(id)
}

func (s *Server) controlExperiment(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}
	var req ControlRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}
	if err := s.db.UpdateExecutionControl(id, req.Command); err != nil {
		return nil, err
	}
	return map[string]string{"status": "updated"}, nil
}

func (s *Server) startExperiment(r *http.Request) (any, error) {
	var req StartExperimentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	cwd, _ := os.Getwd()
	configPath := filepath.Join(cwd, "experiments", "templates", req.TemplateID, "config.yaml")
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		return nil, NewAPIError(http.StatusNotFound, fmt.Sprintf("Template config not found at %s", configPath))
	}

	args := []string{
		"-config", configPath,
		"-reps", strconv.Itoa(req.Reps),
		"-concurrent", strconv.Itoa(req.Concurrent),
	}
	if req.Name != "" {
		args = append(args, "-name", req.Name)
	}
	if req.Control != "" {
		args = append(args, "-control", req.Control)
	}
	if req.Timeout != "" {
		args = append(args, "-timeout", req.Timeout)
	}
	if len(req.Alternatives) > 0 {
		args = append(args, "-alternatives", strings.Join(req.Alternatives, ","))
	}
	if len(req.Scenarios) > 0 {
		args = append(args, "-scenarios", strings.Join(req.Scenarios, ","))
	}

	log.Printf("[Server] Spawning tenkai: %v", args)

	exe, err := os.Executable()
	if err != nil {
		exe = "tenkai"
	}
	cmd := exec.Command(exe, args...)
	cmd.Dir = cwd
	cmd.Env = os.Environ()
	// Capture stdout/stderr for debugging runner failures
	var runnerOut, runnerErr bytes.Buffer
	cmd.Stdout = &runnerOut
	cmd.Stderr = &runnerErr

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("failed to spawn runner: %w", err)
	}
	go func() {
		if err := cmd.Wait(); err != nil {
			log.Printf("[Server] Runner process %d exited with error: %v", cmd.Process.Pid, err)
			log.Printf("[Server] Runner Stderr: %s", runnerErr.String())
			log.Printf("[Server] Runner Stdout: %s", runnerOut.String())
		} else {
			log.Printf("[Server] Runner process %d finished successfully", cmd.Process.Pid)
		}
	}()

	return map[string]string{"message": "Experiment started", "pid": strconv.Itoa(cmd.Process.Pid)}, nil
}

func (s *Server) getRunFiles(r *http.Request) (any, error) {

	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid Run ID")
	}
	res, err := s.db.GetRunFiles(id)
	if err != nil {
		return nil, err
	}
	if res == nil {
		return []interface{}{}, nil
	}
	return res, nil
}

func (s *Server) getRunTests(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid Run ID")
	}
	res, err := s.db.GetTestResults(id)
	if err != nil {
		return nil, err
	}
	if res == nil {
		return []interface{}{}, nil
	}
	return res, nil
}
func (s *Server) getRunLint(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid Run ID")
	}
	res, err := s.db.GetLintResults(id)
	if err != nil {
		return nil, err
	}
	if res == nil {
		return []interface{}{}, nil
	}
	return res, nil
}

func (s *Server) getRunTools(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid Run ID")
	}
	res, err := s.db.GetToolUsage(id)
	if err != nil {
		return nil, err
	}
	if res == nil {
		return []interface{}{}, nil
	}
	return res, nil
}

func (s *Server) getRunMessages(r *http.Request) (any, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid Run ID")
	}
	res, err := s.db.GetMessages(id)

	if err != nil {
		return nil, err
	}
	if res == nil {
		return []interface{}{}, nil
	}
	return res, nil
}

func (s *Server) listScenarios(r *http.Request) (any, error) {
	return s.wsMgr.ListScenarios(), nil
}

func (s *Server) createScenario(r *http.Request) (any, error) {
	if err := r.ParseMultipartForm(32 << 20); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Failed to parse form")
	}
	name := r.FormValue("name")
	desc := r.FormValue("description")
	task := r.FormValue("prompt")

	var assets []config.Asset
	assetType := r.FormValue("asset_type")

	if assetType == "folder" || assetType == "files" {
		files := r.MultipartForm.File["files"]
		for _, fileHeader := range files {
			f, err := fileHeader.Open()
			if err != nil {
				return nil, fmt.Errorf("failed to open uploaded file: %w", err)
			}
			content, err := io.ReadAll(f)
			f.Close()
			if err != nil {
				return nil, fmt.Errorf("failed to read uploaded file: %w", err)
			}

			// Use Filename as target. Browser might send relative path in Filename if webkitdirectory used?
			// Usually Filename is just basename unless standardized.
			// But for single files it's basename.
			assets = append(assets, config.Asset{
				Type:    "file",
				Target:  fileHeader.Filename,
				Content: string(content),
			})
		}
	} else if assetType == "git" {
		assets = append(assets, config.Asset{
			Type:   "git",
			Source: r.FormValue("git_url"),
			Ref:    r.FormValue("git_ref"),
			Target: ".",
		})
	}

	var validation []config.ValidationRule
	valJSON := r.FormValue("validation")
	if valJSON != "" {
		if err := json.Unmarshal([]byte(valJSON), &validation); err != nil {
			log.Printf("Warning: failed to parse validation JSON: %v", err)
		}
	}

	id, err := s.wsMgr.CreateScenario(name, desc, task, assets, validation)
	if err != nil {
		return nil, err
	}
	return map[string]string{"id": id, "name": name}, nil
}

func (s *Server) getScenario(r *http.Request) (any, error) {
	id := r.PathValue("id")
	return s.wsMgr.GetScenario(id)
}

func (s *Server) listTemplates(r *http.Request) (any, error) {
	return s.wsMgr.ListTemplates(), nil
}
func (s *Server) createTemplate(r *http.Request) (any, error) {
	var req struct {
		Name        string            `json:"name"`
		Description string            `json:"description"`
		Config      string            `json:"yaml_content"`
		Files       map[string]string `json:"files"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}
	id, err := s.wsMgr.CreateTemplate(req.Name, req.Description, req.Config, req.Files)
	if err != nil {
		return nil, err
	}
	return map[string]string{"id": id, "name": req.Name}, nil
}

func (s *Server) getTemplateConfig(r *http.Request) (any, error) {

	id := r.PathValue("id")
	tmpl, err := s.wsMgr.GetTemplate(id)
	if err != nil {
		return nil, NewAPIError(http.StatusNotFound, err.Error())
	}

	var cfgMap map[string]interface{}
	if err := yaml.Unmarshal([]byte(tmpl.ConfigContent), &cfgMap); err != nil {
		log.Printf("Warning: failed to parse config YAML: %v", err)
	}

	return map[string]interface{}{
		"name":    tmpl.Name,
		"content": tmpl.ConfigContent,
		"config":  cfgMap,
	}, nil
}

func (s *Server) updateTemplate(r *http.Request) (any, error) {
	id := r.PathValue("id")
	var req struct {
		Config string            `json:"yaml_content"`
		Files  map[string]string `json:"files"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	if err := s.wsMgr.UpdateTemplate(id, req.Config, req.Files); err != nil {
		if strings.Contains(err.Error(), "not found") {
			return nil, NewAPIError(http.StatusNotFound, err.Error())
		}
		return nil, err
	}

	return map[string]string{"status": "updated"}, nil
}

func (s *Server) updateScenario(r *http.Request) (any, error) {
	id := r.PathValue("id")
	var req struct {
		Name        string                  `json:"name"`
		Description string                  `json:"description"`
		Task        string                  `json:"task"`
		Validation  []config.ValidationRule `json:"validation"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	if err := s.wsMgr.UpdateScenario(id, req.Name, req.Description, req.Task, req.Validation); err != nil {
		if strings.Contains(err.Error(), "not found") {
			return nil, NewAPIError(http.StatusNotFound, err.Error())
		}
		return nil, err
	}

	return map[string]string{"status": "updated"}, nil
}

func (s *Server) deleteScenario(r *http.Request) (any, error) {
	id := r.PathValue("id")
	if err := s.wsMgr.DeleteScenario(id); err != nil {
		if strings.Contains(err.Error(), "not found") {
			return nil, NewAPIError(http.StatusNotFound, err.Error())
		}
		return nil, err
	}
	return map[string]string{"status": "deleted"}, nil
}

func (s *Server) deleteTemplate(r *http.Request) (any, error) {
	id := r.PathValue("id")
	if err := s.wsMgr.DeleteTemplate(id); err != nil {
		if strings.Contains(err.Error(), "not found") {
			return nil, NewAPIError(http.StatusNotFound, err.Error())
		}
		return nil, err
	}
	return map[string]string{"status": "deleted"}, nil
}

func (s *Server) deleteAllTemplates(r *http.Request) (any, error) {
	if err := s.wsMgr.DeleteAllTemplates(); err != nil {
		return nil, err
	}
	return map[string]string{"status": "all deleted"}, nil
}

func (s *Server) legacyControlExperiment(r *http.Request) (any, error) {
	var req struct {
		ID     any    `json:"id"` // can be string or number from frontend
		Action string `json:"action"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	var id int64
	switch v := req.ID.(type) {
	case string:
		id, _ = strconv.ParseInt(v, 10, 64)
	case float64:
		id = int64(v)
	case int:
		id = int64(v)
	case int64:
		id = v
	}

	if id == 0 {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}

	if err := s.db.UpdateExecutionControl(id, req.Action); err != nil {
		return nil, err
	}
	return map[string]string{"status": "updated"}, nil
}

func (s *Server) relaunchExperiment(r *http.Request) (any, error) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}

	exp, err := s.db.GetExperimentByID(id)
	if err != nil {
		return nil, err
	}

	if exp.ConfigPath == "" {
		return nil, NewAPIError(http.StatusBadRequest, "Experiment has no config path and cannot be relaunched")
	}

	// Spawning a new tenkai process with the original config
	cwd, _ := os.Getwd()
	args := []string{" -config", exp.ConfigPath}
	if exp.Name != "" {
		args = append(args, "-name", exp.Name+" (Relaunch)")
	}

	exe, err := os.Executable()
	if err != nil {
		exe = "tenkai"
	}
	cmd := exec.Command(exe, args...)
	cmd.Dir = cwd
	cmd.Env = os.Environ()

	var runnerOut, runnerErr bytes.Buffer
	cmd.Stdout = &runnerOut
	cmd.Stderr = &runnerErr

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("failed to relaunch runner: %w", err)
	}
	go func() {
		if err := cmd.Wait(); err != nil {
			log.Printf("[Server] Relaunched runner %d exited with error: %v", cmd.Process.Pid, err)
			log.Printf("[Server] Runner Stderr: %s", runnerErr.String())
		}
	}()

	return map[string]string{"message": "Experiment relaunched", "pid": strconv.Itoa(cmd.Process.Pid)}, nil
}

func (s *Server) handleExportReport(w http.ResponseWriter, r *http.Request) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		http.Error(w, "Invalid ID", http.StatusBadRequest)
		return
	}

	exp, err := s.db.GetExperimentByID(id)
	if err != nil {
		http.Error(w, "Not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "text/markdown")
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"report-%d.md\"", id))
	w.Write([]byte(exp.ReportContent))
}

func (s *Server) saveAIAnalysis(r *http.Request) (any, error) {
	idStr := r.PathValue("id")
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		return nil, NewAPIError(http.StatusBadRequest, "Invalid ID")
	}

	var req struct {
		Analysis string `json:"analysis"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, NewAPIError(http.StatusBadRequest, err.Error())
	}

	if err := s.db.UpdateExperimentAIAnalysis(id, req.Analysis); err != nil {
		return nil, err
	}

	return map[string]string{"status": "saved"}, nil
}

func (s *Server) handleLogs(r *http.Request) (any, error) {
	cwd, _ := os.Getwd()
	logPath := filepath.Join(cwd, "tenkai.log")
	if _, err := os.Stat(logPath); os.IsNotExist(err) {
		return map[string]string{"logs": "(No logs found)"}, nil
	}

	// Read last 1000 lines
	cmd := exec.Command("tail", "-n", "1000", logPath)
	out, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to read logs: %w", err)
	}

	return map[string]string{"logs": string(out)}, nil
}
