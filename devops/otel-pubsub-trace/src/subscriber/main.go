// Copyright 2023 Google LLC
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
	"encoding/json"
	"log"
	"os"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.11.0"
	"go.opentelemetry.io/otel/trace"

	"cloud.google.com/go/compute/metadata"
	"cloud.google.com/go/pubsub"
	cloudtrace "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/trace"
)

const (
	ServiceName    = "subscriber-service"
	SubscriberName = "subscriber"
)

func initTracer() (func(), error) {
	exporter, err := cloudtrace.New()
	if err != nil {
		return nil, err
	}
	sname := os.Getenv("SERVICE_NAME")
	if sname == "" {
		sname = ServiceName
	}
	res, err := resource.New(
		context.Background(),
		resource.WithAttributes(
			semconv.ServiceNameKey.String(sname),
			semconv.ServiceVersionKey.String("1.0.0"),
			semconv.DeploymentEnvironmentKey.String("production"),
			semconv.TelemetrySDKNameKey.String("opentelemetry"),
			semconv.TelemetrySDKLanguageKey.String("go"),
		),
	)
	if err != nil {
		return nil, err
	}
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	return func() {
		err := tp.Shutdown(context.Background())
		if err != nil {
			log.Fatalf("error shutting down trace provider: %v", err)
		}
	}, nil
}

func main() {
	ctx := context.Background()
	meta := metadata.NewClient(nil)

	shutdown, err := initTracer()
	if err != nil {
		log.Fatal(err)
	}
	defer shutdown()

	// Initialize Pub/Sub client
	projectID, err := meta.ProjectID()
	if err != nil {
		log.Fatalf("failed to find project ID: %v", err)
	}
	log.Printf("subscriber project ID: %v", projectID)
	client, err := pubsub.NewClient(ctx, projectID)
	if err != nil {
		log.Fatalf("failed to create Pub/Sub client: %v", err)
	}
	defer client.Close()

	subscriber(ctx, client)
}

func subscriber(ctx context.Context, client *pubsub.Client) {
	sname := os.Getenv("SUBSCRIBER_NAME")
	if sname == "" {
		sname = SubscriberName
	}
	sub := client.Subscription(sname)
	err := sub.Receive(ctx, handler)
	if err != nil {
		log.Printf("error subscribing topic: %v", err)
	}
}

func handler(ctx context.Context, msg *pubsub.Message) {
	if msg.Attributes != nil {
		propagator := otel.GetTextMapPropagator()
		ctx = propagator.Extract(ctx, propagation.MapCarrier(msg.Attributes))
	}
	sname := os.Getenv("SUBSCRIBER_NAME")
	if sname == "" {
		sname = SubscriberName
	}
	options := []trace.SpanStartOption{
		trace.WithSpanKind(trace.SpanKindConsumer),
		trace.WithAttributes(
			semconv.MessagingSystemKey.String("pubsub"),
			semconv.MessagingDestinationKey.String(sname),
			semconv.MessagingDestinationKindTopic,
			semconv.MessagingMessageIDKey.String(msg.ID),
		),
	}
	ctx, span := otel.Tracer("subscriber").Start(ctx, "subscribe-pubsub", options...)
	defer span.End()

	var data map[string]string
	err := json.Unmarshal(msg.Data, &data)
	if err != nil {
		log.Printf("failed to unmarshal data: %v", err)
		msg.Nack()
		return
	}
	log.Printf("message data: %v", msg.Data)

	_, subspan := otel.Tracer("subscriber").Start(ctx, "call-process-user", options...)
	processUser(data["user_id"])
	msg.Ack()
	subspan.End()
}

func processUser(id string) {
	// emulate blocking operation
	time.Sleep(100 * time.Millisecond)
	log.Printf("received data -> user_id: %v", id)
}
