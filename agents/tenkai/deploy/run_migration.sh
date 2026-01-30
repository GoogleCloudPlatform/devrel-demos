#!/bin/bash
set -e

# Configuration
PROJECT_ID="daniela-genai-sandbox"
DB_PASS="Hy19bhuEyMhoU8Bi"
INSTANCE_CONNECTION_NAME="daniela-genai-sandbox:us-central1:tenkai-db"

# Start Proxy
echo "Starting Cloud SQL Proxy..."
./cloud_sql_proxy "$INSTANCE_CONNECTION_NAME" --port 5432 > proxy.log 2>&1 &
PROXY_PID=$!

echo "Waiting for proxy to start..."
sleep 5

# Run Migration
echo "Running Migration..."
# Using go run with flags
go run cmd/migrate_data/main.go \
    --sqlite "experiments/tenkai.db" \
    --pg-dsn "postgres://tenkai:$DB_PASS@127.0.0.1:5432/tenkai?sslmode=disable"

# Cleanup
echo "Killing Proxy..."
kill $PROXY_PID
echo "Done."
