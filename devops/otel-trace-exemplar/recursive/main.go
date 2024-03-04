// Copyright 2024 Google LLC
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
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"os"
	"strconv"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/metric"
	"go.opentelemetry.io/otel/propagation"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.4.0"
)

const (
	spanInterval = 50 * time.Millisecond
	genInterval  = 10 * time.Second
)

var (
	OTLPEndpoint = "localhost:4317"
	ServiceName  = "default-service"

	histogram metric.Int64Histogram
)

// newResource returns a OpenTelemetry resource object of the service
func newResource(name, version, env string) (*resource.Resource, error) {
	return resource.New(
		context.Background(),
		// TODO(yoshifumi): Check how GCP detector works with exemplars.
		// Using detector disables sending metrics with exemplar to the Cloud Monitoring.
		//
		// resource.WithDetectors(gcp.NewDetector()),
		resource.WithTelemetrySDK(),
		resource.WithAttributes(
			semconv.ServiceNameKey.String(name),
			semconv.ServiceVersionKey.String(version),
			semconv.DeploymentEnvironmentKey.String(env),
		),
	)
}

func initTracer() (*sdktrace.TracerProvider, error) {
	e := os.Getenv("OTLP_ENDPOINT")
	if e == "" {
		e = OTLPEndpoint
	}

	// OTLP exporter config for Collector (using default config)
	exporter, err := otlptracegrpc.New(
		context.Background(),
		otlptracegrpc.WithEndpoint(e),
		otlptracegrpc.WithInsecure(),
	)
	if err != nil {
		return nil, err
	}
	sname := os.Getenv("SERVICE_NAME")
	if sname == "" {
		sname = ServiceName
	}
	res, err := newResource(sname, "1.0.0", "demo")
	if err != nil {
		log.Printf("failed to create resource: %v", err)
		return nil, err
	}
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	return tp, nil
}

func initMeter() (*sdkmetric.MeterProvider, error) {
	e := os.Getenv("OTLP_ENDPOINT")
	if e == "" {
		e = OTLPEndpoint
	}

	exporter, err := otlpmetricgrpc.New(
		context.Background(),
		otlpmetricgrpc.WithEndpoint(e),
		otlpmetricgrpc.WithInsecure(),
	)
	if err != nil {
		return nil, err
	}
	sname := os.Getenv("SERVICE_NAME")
	if sname == "" {
		sname = ServiceName
	}
	res, err := newResource(sname, "1.0.0", "demo")
	if err != nil {
		return nil, err
	}
	mp := sdkmetric.NewMeterProvider(
		sdkmetric.WithReader(sdkmetric.NewPeriodicReader(
			exporter,
			sdkmetric.WithInterval(1*time.Minute),
		)),
		sdkmetric.WithResource(res),
	)
	otel.SetMeterProvider(mp)
	return mp, nil
}

func main() {
	log.Print("starting tracer provider")
	tp, err := initTracer()
	if err != nil {
		log.Fatalf("failed to start OpenTelemetry Trace config: %v", err)
	}
	mp, err := initMeter()
	if err != nil {
		log.Fatalf("failed to start OpenTelemetry Meter config: %v", err)
	}
	defer func() {
		if err := tp.Shutdown(context.Background()); err != nil {
			log.Fatalf("failed to shutdown TraceProvider: %v", err)
		}
		if err := mp.Shutdown(context.Background()); err != nil {
			log.Fatalf("failed to shutdown MeterProvider: %v", err)
		}
	}()
	log.Print("launch telemetry data generator")

	meter := mp.Meter("demo")
	histogram, err = meter.Int64Histogram(
		"exemplar/root.latency",
		metric.WithDescription("latency of the root handler"),
		metric.WithUnit("ms"),
	)
	if err != nil {
		log.Fatalf("failed to initialize histogram: %v", err)
	}

	http.HandleFunc("/_hello", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})
	otelHandler := otelhttp.NewHandler(http.HandlerFunc(root), "client.handler")
	http.Handle("/root", otelHandler)
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatalf("failed to start server: %v", err)
	}
}

func root(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	q := r.URL.Query()
	n := rand.Intn(10) + 1
	nstr := q.Get("n")
	if nstr != "" {
		n, _ = strconv.Atoi(nstr)
	}

	ctx, span := otel.Tracer("handler").Start(ctx, "sample.root")
	start := time.Now()
	foo(ctx, n)
	duration := time.Since(start)
	histogram.Record(
		ctx,
		int64(duration.Milliseconds()),
	)
	span.End()
	fmt.Fprintf(w, "run %vth fib", n)
}

func foo(ctx context.Context, n int) {
	if n == 0 {
		return
	}
	ctx, span := otel.Tracer("handler").Start(ctx, "sample.foo")
	span.SetAttributes(attribute.Key("iteration").Int(n))
	time.Sleep(spanInterval)
	span.AddEvent(fmt.Sprintf("mid-interval-%v", n))
	time.Sleep(spanInterval)
	foo(ctx, n-1)
	span.End()
}
