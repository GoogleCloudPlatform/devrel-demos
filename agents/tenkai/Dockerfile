# Build Stage
FROM golang:1.24 as builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

# Build the Tenkai binary
# CGO_ENABLED=1 might be needed for sqlite, but modernc.org/sqlite is pure Go.
# Let's check go.mod. It uses modernc.org/sqlite.
# So CGO_ENABLED=0 should be fine and produces a static binary.
RUN CGO_ENABLED=0 GOOS=linux go build -o tenkai .

# Runtime Stage
FROM gcr.io/distroless/static:nonroot

WORKDIR /

COPY --from=builder /app/tenkai /tenkai
# Copy templates and scenarios if they are strictly needed at runtime by the binary 
# (The binary reads them from disk)
COPY --from=builder /app/experiments /experiments
COPY --from=builder /app/scenarios /scenarios
COPY --from=builder /app/internal /internal 
# Wait, copying /internal source is weird. 
# The runner copies ASSETS from scenarios.
# It might need `common/` or `policies/` if they exist.
# Let's assume standard structure.

# Helper for the binary to find assets
ENV TENKAI_TEMPLATES_DIR=/experiments/templates
ENV TENKAI_SCENARIOS_DIR=/scenarios

# Expose port (Cloud Run defaults to 8080)
EXPOSE 8080

ENTRYPOINT ["/tenkai"]
