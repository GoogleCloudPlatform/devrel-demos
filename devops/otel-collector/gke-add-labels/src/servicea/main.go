package main

import (
	"context"
	"crypto/rand"
	"fmt"
	"log"
	"math/big"
	"os"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.11.0"
)

const (
	spanInterval = 50 * time.Millisecond
	genInterval  = 1 * time.Second
)

var OTLPEndpoint = "localhost:4317"

func initTracer() (*sdktrace.TracerProvider, error) {
	e := os.Getenv("OTLP_ENDPOINT")
	if e != "" {
		OTLPEndpoint = e
	}

	// OTLP exporter config for Collector (using default config)
	exporter, err := otlptracegrpc.New(
		context.Background(),
		otlptracegrpc.WithInsecure(),
	)
	if err != nil {
		return nil, err
	}
	res, err := resource.New(
		context.Background(),
		resource.WithAttributes(
			semconv.ServiceNameKey.String("service-a"),
			semconv.ServiceVersionKey.String("1.0.0"),
			semconv.DeploymentEnvironmentKey.String("production"),
			semconv.TelemetrySDKNameKey.String("opentelemetry"),
			semconv.TelemetrySDKLanguageKey.String("go"),
			semconv.TelemetrySDKVersionKey.String("0.13.0"),
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
	return tp, nil
}

func main() {
	log.Print("starting tracer provider")
	tp, err := initTracer()
	if err != nil {
		log.Fatalf("failed to start OpenTelemetry Trace config: %v", err)
	}
	defer func() {
		if err := tp.Shutdown(context.Background()); err != nil {
			log.Fatalf("failed to shutdown TraceProvider: %v", err)
		}
	}()
	log.Print("launch trace generator")

	traceGenerator(genInterval)
}

func traceGenerator(d time.Duration) {
	t := time.NewTicker(d)
	for range t.C {
		n, err := rand.Int(rand.Reader, big.NewInt(10))
		if err != nil {
			log.Printf("error on generating random int: %v", err)
		}
		root(int(n.Int64()))
	}
}

func root(n int) {
	ctx := context.Background()
	ctx, span := otel.Tracer("handler").Start(ctx, "sample.root.call.foo")
	foo(ctx, n)
	span.End()
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
