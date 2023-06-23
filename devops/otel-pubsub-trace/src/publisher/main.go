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
	"io"
	"log"
	"net/http"
	"os"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.11.0"
	"go.opentelemetry.io/otel/trace"

	"cloud.google.com/go/compute/metadata"
	"cloud.google.com/go/pubsub"
	cloudtrace "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/trace"
	"github.com/google/uuid"
)

const (
	ServiceName = "publisher-service"
	TopicName   = "otel-pubsub-topic"
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
	log.Printf("publisher project ID: %v", projectID)
	client, err := pubsub.NewClient(ctx, projectID)
	if err != nil {
		log.Fatalf("failed to create Pub/Sub client: %v", err)
	}
	defer client.Close()
	hh := &helloHandler{
		pubsubClient: client,
	}

	otelHandler := otelhttp.NewHandler(http.HandlerFunc(hh.Handler), "hello")
	http.Handle(("/hello"), otelHandler)
	err = http.ListenAndServe(":8080", nil)
	if err != nil {
		log.Fatal(err)
	}
}

type helloHandler struct {
	pubsubClient *pubsub.Client
}

func (hh *helloHandler) Handler(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	span := trace.SpanFromContext(ctx)
	defer span.End()

	// Prepare pubsub message publish
	topic := hh.pubsubClient.Topic(TopicName)
	data := map[string]string{
		"user_id":  getUserID(),
		"order_id": getOrderID(),
	}
	m, err := json.Marshal(data)
	if err != nil {
		log.Printf("error marshaling data: %v", err)
		http.Error(w, "Bad Request: marshaling data", http.StatusBadRequest)
		return
	}
	msg := pubsub.Message{Data: m}

	// Create subspan to send message to pubsub
	options := []trace.SpanStartOption{
		trace.WithSpanKind(trace.SpanKindProducer),
		trace.WithAttributes(
			semconv.MessagingSystemKey.String("pubsub"),
			semconv.MessagingDestinationKey.String(TopicName),
			semconv.MessagingDestinationKindTopic,
		),
	}
	if msg.Attributes == nil {
		msg.Attributes = make(map[string]string)
	}
	otel.GetTextMapPropagator().Inject(ctx, propagation.MapCarrier(msg.Attributes))

	_, subspan := otel.Tracer("publisher").Start(ctx, "send-to-pubsub", options...)
	defer subspan.End()

	msgId, err := topic.Publish(ctx, &msg).Get(ctx)
	if err != nil {
		log.Printf("failed to publish message: %v", err)
		http.Error(w, "Bad Request: publish message", http.StatusBadRequest)
		return
	}
	subspan.SetAttributes(semconv.MessagingMessageIDKey.String(msgId))

	io.WriteString(w, "hello")
}

func getUserID() string {
	return uuid.NewString()
}

func getOrderID() string {
	return uuid.NewString()
}
