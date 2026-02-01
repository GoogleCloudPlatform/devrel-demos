#!/bin/bash

# Tenkai Database Migration Script
# SQLite -> Cloud SQL (PostgreSQL 18)

# Configuration
PROJECT_ID=${PROJECT_ID}
REGION=${REGION}
DB_INSTANCE_NAME=${DB_INSTANCE_NAME:-"tenkai-db"}
INSTANCE_CONNECTION_NAME="${PROJECT_ID}:${REGION}:${DB_INSTANCE_NAME}"
DB_NAME="tenkai"
DB_PASS_POSTGRES="TenkaiPostgres2026!"
DB_PASS_MIGRATION="TenkaiMigration2026!"
PROXY_PORT=5434

echo "----------------------------------------------------------"
echo "Starting Tenkai Database Migration"
echo "----------------------------------------------------------"

# Start Cloud SQL Proxy in the background
echo "[1/4] Starting Cloud SQL Proxy..."
./cloud_sql_proxy $INSTANCE_CONNECTION_NAME --port $PROXY_PORT &
PROXY_PID=$!

# Give the proxy a few seconds to initialize
sleep 5

# Define DSNs
DSN_POSTGRES="postgres://postgres:$DB_PASS_POSTGRES@127.0.0.1:$PROXY_PORT/$DB_NAME?sslmode=disable"
DSN_MIGRATION="postgres://migration_admin:$DB_PASS_MIGRATION@127.0.0.1:$PROXY_PORT/$DB_NAME?sslmode=disable"

# Step 1: Cleanup and Schema Setup (Superuser)
echo "[2/4] Resetting schema and permissions (as postgres)..."

# Check if psql is available
if command -v psql &> /dev/null; then
    echo "psql found, using it."
    export PGPASSWORD=$DB_PASS_POSTGRES
    psql "$DSN_POSTGRES" -f sql/drop_all_tables.sql
    psql "$DSN_POSTGRES" -f sql/postgres_schema.sql
    psql "$DSN_POSTGRES" -f sql/grant_permissions.sql
else
    # Fallback to migrate_tool.go (if it exists, but we are deleting it)
    # If we deleted it, we must ensure we don't try to run it.
    echo "Error: psql not found. Please install psql or libpq."
    kill $PROXY_PID
    exit 1
fi

if [ $? -ne 0 ]; then
    echo "Error: Schema setup failed."
    kill $PROXY_PID
    exit 1
fi

# Step 2: Data Migration (Migration Admin)
echo "[3/4] Migrating data (as migration_admin)..."
DB_DSN=$DSN_MIGRATION go run sql/migrate.go

if [ $? -ne 0 ]; then
    echo "Error: Data migration failed."
    kill $PROXY_PID
    exit 1
fi

# Cleanup
echo "[4/4] Shutting down proxy..."
kill $PROXY_PID

echo "----------------------------------------------------------"
echo "Migration Successfully Completed!"
echo "----------------------------------------------------------"
