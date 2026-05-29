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

type GoogleResultSubscriber struct {
	client *pubsub.Client
	sub    *pubsub.Subscription
}

func NewGoogleResultSubscriber(projectID, subID string) (*GoogleResultSubscriber, error) {
	ctx := context.Background()
	client, err := pubsub.NewClient(ctx, projectID)
	if err != nil {
		return nil, err
	}

	sub := client.Subscription(subID)
	return &GoogleResultSubscriber{
		client: client,
		sub:    sub,
	}, nil
}

// Start listens for messages and passes them to the provided handler. It blocks until ctx is canceled or an error occurs.
func (s *GoogleResultSubscriber) Start(ctx context.Context, handle func(domain.JudgingResult) error) error {
	log.Printf("Listening for messages on subscription: %s", s.sub.String())
	return s.sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
		var result domain.JudgingResult
		if err := json.Unmarshal(msg.Data, &result); err != nil {
			log.Printf("Failed to unmarshal judging result: %v", err)
			msg.Nack()
			return
		}

		if err := handle(result); err != nil {
			log.Printf("Failed to handle judging result: %v", err)
			msg.Nack()
			return
		}

		msg.Ack()
	})
}
