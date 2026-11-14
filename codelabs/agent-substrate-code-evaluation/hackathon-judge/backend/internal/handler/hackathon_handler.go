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

package handler

import (
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/moficodes/hackathon-judge/backend/internal/service"
)

type HackathonHandler struct {
	svc service.HackathonService
}

func NewHackathonHandler(svc service.HackathonService) *HackathonHandler {
	return &HackathonHandler{svc: svc}
}

func (h *HackathonHandler) RegisterRoutes(r *gin.Engine) {
	api := r.Group("/api")
	{
		api.GET("/hackathons", h.GetHackathons)
		api.GET("/hackathons/:id", h.GetHackathon)
		api.GET("/hackathons/:id/projects", h.GetProjects)
		api.GET("/projects/:id", h.GetProject)
		api.GET("/projects/:id/evaluations", h.GetEvaluations)
		api.POST("/projects/:id/judge", h.TriggerJudgingAgent)
	}
}

func (h *HackathonHandler) GetHackathons(c *gin.Context) {
	res, err := h.svc.ListHackathons()
	if err != nil {
		log.Printf("[ERROR] GetHackathons failed: %v\n", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, res)
}

func (h *HackathonHandler) GetHackathon(c *gin.Context) {
	id := c.Param("id")
	res, err := h.svc.GetHackathon(id)
	if err != nil {
		log.Printf("[ERROR] GetHackathon failed for %s: %v\n", id, err)
		c.JSON(http.StatusNotFound, gin.H{"error": "Hackathon not found"})
		return
	}
	c.JSON(http.StatusOK, res)
}

func (h *HackathonHandler) GetProjects(c *gin.Context) {
	id := c.Param("id")
	res, err := h.svc.ListProjectsByHackathon(id)
	if err != nil {
		log.Printf("[ERROR] GetProjects failed for hackathon %s: %v\n", id, err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, res)
}

func (h *HackathonHandler) GetProject(c *gin.Context) {
	id := c.Param("id")
	res, err := h.svc.GetProject(id)
	if err != nil {
		log.Printf("[ERROR] GetProject failed for %s: %v\n", id, err)
		c.JSON(http.StatusNotFound, gin.H{"error": "Project not found"})
		return
	}
	c.JSON(http.StatusOK, res)
}

func (h *HackathonHandler) GetEvaluations(c *gin.Context) {
	id := c.Param("id")
	res, err := h.svc.ListEvaluationsByProject(id)
	if err != nil {
		// Use a simple string check to determine if the project wasn't found
		if err.Error() == "failed to get project: project not found" {
			log.Printf("[WARNING] GetEvaluations project not found: %s\n", id)
			c.JSON(http.StatusNotFound, gin.H{"error": "Project not found"})
			return
		}
		log.Printf("[ERROR] GetEvaluations failed for project %s: %v\n", id, err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, res)
}

func (h *HackathonHandler) TriggerJudgingAgent(c *gin.Context) {
	id := c.Param("id")
	taskID, err := h.svc.TriggerJudgingAgent(id)
	if err != nil {
		log.Printf("[ERROR] TriggerJudgingAgent failed for project %s: %v\n", id, err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusAccepted, gin.H{
		"message": "Agent judging task created",
		"task_id": taskID,
	})
}
