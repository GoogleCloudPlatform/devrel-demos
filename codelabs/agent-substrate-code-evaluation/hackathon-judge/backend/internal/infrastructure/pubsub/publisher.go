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

package pubsub

import (
	"context"
	"encoding/json"
	"log"

	"cloud.google.com/go/pubsub"
	"github.com/moficodes/hackathon-judge/backend/internal/domain"
)

type GoogleTaskPublisher struct {
	client *pubsub.Client
	topic  *pubsub.Topic
}

func NewGoogleTaskPublisher(projectID, topicID string) (*GoogleTaskPublisher, error) {
	ctx := context.Background()
	client, err := pubsub.NewClient(ctx, projectID)
	if err != nil {
		return nil, err
	}

	topic := client.Topic(topicID)
	return &GoogleTaskPublisher{
		client: client,
		topic:  topic,
	}, nil
}

func (p *GoogleTaskPublisher) PublishTask(task domain.JudgingTask) error {
	ctx := context.Background()
	
	data, err := json.Marshal(task)
	if err != nil {
		return err
	}

	result := p.topic.Publish(ctx, &pubsub.Message{
		Data: data,
	})

	id, err := result.Get(ctx)
	if err != nil {
		log.Printf("Failed to publish task: %v", err)
		return err
	}

	log.Printf("Published judging task %s as message ID %s", task.TaskID, id)
	return nil
}
