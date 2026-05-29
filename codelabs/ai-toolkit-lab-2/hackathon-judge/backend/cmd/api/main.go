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

package main

import (
	"context"
	"log"
	"os"

	"cloud.google.com/go/bigquery"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"github.com/moficodes/hackathon-judge/backend/internal/domain"
	"github.com/moficodes/hackathon-judge/backend/internal/handler"
	"github.com/moficodes/hackathon-judge/backend/internal/infrastructure/pubsub"
	"github.com/moficodes/hackathon-judge/backend/internal/repository"
	"github.com/moficodes/hackathon-judge/backend/internal/service"
	"github.com/moficodes/hackathon-judge/backend/pkg/logger"
)

const defaultPort = ":8080"

func main() {
	logger.Init()

	// Load .env file if it exists
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found, relying on environment variables")
	}

	r := gin.Default()

	projectID := os.Getenv("GOOGLE_CLOUD_PROJECT")
	if projectID == "" {
		log.Fatal("GOOGLE_CLOUD_PROJECT environment variable is required")
	}
	topicID := os.Getenv("TASKS_TOPIC")
	if topicID == "" {
		log.Fatal("TASKS_TOPIC environment variable is required")
	}
	subID := os.Getenv("RESULTS_SUB")
	if subID == "" {
		log.Fatal("RESULTS_SUB environment variable is required")
	}
	datasetID := os.Getenv("BQ_DATASET")
	if datasetID == "" {
		datasetID = "hackathon_judge"
	}

	publisher, err := pubsub.NewGoogleTaskPublisher(projectID, topicID)
	if err != nil {
		log.Printf("Warning: failed to initialize PubSub publisher: %v. Using mock.", err)
		publisher = nil
	}

	var hackathonRepo domain.HackathonRepository
	var projectRepo domain.ProjectRepository
	var evalRepo domain.EvaluationRepository

	bqClient, err := bigquery.NewClient(context.Background(), projectID)
	if err != nil {
		log.Printf("Warning: failed to initialize BigQuery client: %v. Falling back to MemoryRepo.", err)
		memRepo := repository.NewMemoryRepo()
		hackathonRepo = memRepo
		projectRepo = memRepo
		evalRepo = memRepo
	} else {
		log.Println("Successfully initialized BigQuery client.")
		bqRepo := repository.NewBigQueryRepo(bqClient, projectID, datasetID)
		hackathonRepo = bqRepo
		projectRepo = bqRepo
		evalRepo = bqRepo
	}

	svc := service.NewHackathonService(hackathonRepo, projectRepo, evalRepo, publisher)

	subscriber, err := pubsub.NewGoogleResultSubscriber(projectID, subID)
	if err != nil {
		log.Printf("Warning: failed to initialize PubSub subscriber: %v. Result listening disabled.", err)
	} else {
		go func() {
			log.Println("Starting background result subscriber...")
			err := subscriber.Start(context.Background(), func(res domain.JudgingResult) error {
				log.Printf("--- RECEIVED JUDGING RESULT ---")
				log.Printf("Task ID: %s", res.TaskID)
				log.Printf("Status: %s", res.Status)
				
				err := svc.SaveJudgingResult(res)
				if err != nil {
					log.Printf("Failed to process judging result: %v", err)
					return err
				}

				log.Printf("Successfully processed result for task %s", res.TaskID)
				log.Printf("-------------------------------")
				return nil
			})
			if err != nil {
				log.Printf("Subscriber stopped with error: %v", err)
			}
		}()
	}

	h := handler.NewHackathonHandler(svc)

	h.RegisterRoutes(r)

	log.Printf("Server starting on %s\n", defaultPort)
	if err := r.Run(defaultPort); err != nil {
		log.Fatal(err)
	}
}
