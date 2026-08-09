#!/bin/bash
set -e

# Navigate to the script's directory
cd "$(dirname "$0")"

# Print Welcome Banner
echo "=========================================================="
echo "📊  Local Stateless Grafana with BigQuery Connector"
echo "=========================================================="

# Check if Docker daemon is running
if ! docker info >/dev/null 2>&1; then
  echo "⚠️  Docker daemon is not running!"
  
  # Check if Colima is available as an alternative container runtime
  if command -v colima >/dev/null 2>&1; then
    echo "ℹ️  Colima is detected on your system. Starting Colima..."
    echo "👉 Running: colima start"
    colima start
  else
    echo "❌ Error: Docker daemon is inactive, and Colima was not found."
    echo "   Please start Docker Desktop, Colima, or your active container runtime, then try again."
    exit 1
  fi
fi

# Set default port and admin credentials if not set
export GRAFANA_PORT=${GRAFANA_PORT:-3000}
export GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}

# Load environment variables from .env file at repo root if it exists
if [ -f "../.env" ]; then
  echo "📝 Sourced environment parameters dynamically from root .env file."
  export $(grep -v '^#' ../.env | xargs)
elif [ -f ".env" ]; then
  echo "📝 Sourced environment parameters dynamically from local .env file."
  export $(grep -v '^#' .env | xargs)
fi

if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
  echo "⚠️  WARNING: GOOGLE_CLOUD_PROJECT is not set in your shell environment or .env file."
  echo "   Please make sure to set it so the BigQuery datasource defaults correctly."
else
  echo "🌐 Active Google Cloud Project: $GOOGLE_CLOUD_PROJECT"
fi

# Detect Docker Compose command dynamically
if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "❌ Error: Neither 'docker compose' nor 'docker-compose' command was found."
  echo "   Please ensure Docker Compose is installed."
  exit 1
fi

echo "📦 Building custom Grafana image with pre-installed Google Cloud CLI..."
$COMPOSE_CMD build

echo "🚀 Starting stateless local Grafana container on port $GRAFANA_PORT..."
$COMPOSE_CMD down --remove-orphans > /dev/null 2>&1 || true
$COMPOSE_CMD up -d

echo "----------------------------------------------------------"
echo "🕒 Grafana is starting up..."
echo "👉 Open your web browser to: http://localhost:$GRAFANA_PORT"
echo "🔑 Default Web Credentials:"
echo "   - Username: admin"
echo "   - Password: $GRAFANA_ADMIN_PASSWORD"
echo "----------------------------------------------------------"
echo "🔒 INTERACTIVE CONTAINER-LEVEL AUTHENTICATION"
echo "To log in securely inside the container and create your ADC session, run:"
echo ""
echo "   docker exec -it local-grafana-bigquery gcloud auth application-default login"
echo ""
echo "💡 What this does:"
echo "1. Launches the official Google OAuth flow inside the container."
echo "2. Provides a browser link to open on your host mac."
echo "3. Prompts you to copy-paste the auth code back into the terminal."
echo "4. Securely writes credentials directly to /home/grafana/.config/gcloud/"
echo "   which Grafana immediately uses to safely query your BigQuery dataset!"
echo "=========================================================="
