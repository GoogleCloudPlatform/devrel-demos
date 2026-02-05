# ==============================================================================
# Installation & Setup
# ==============================================================================

# Install dependencies using uv package manager
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.8.13/install.sh | sh; source $$HOME/.local/bin/env; }
	uv sync

# ==============================================================================
# Playground Targets
# ==============================================================================

# Launch local dev playground
playground:
	@echo "==============================================================================="
	@echo "| 🚀 Starting your agent playground...                                        |"
	@echo "|                                                                             |"
	@echo "| 💡 Try asking: What's the weather in San Francisco?                         |"
	@echo "|                                                                             |"
	@echo "| 🔍 IMPORTANT: Select the 'app' folder to interact with your agent.          |"
	@echo "==============================================================================="
	uv run adk web . --port 8501 --reload_agents

# ==============================================================================
# Local Development Commands
# ==============================================================================

# Launch local development server with hot-reload
local-backend:
	uv run uvicorn dev_signal_agent.fast_api_app:app --host localhost --port 8000 --reload

# ==============================================================================
# Backend Deployment Targets
# ==============================================================================

# --- Deployment Config ---
PROJECT_ID ?= $(shell gcloud config get-value project)
REGION     ?= us-central1
LOCATION   ?= global
IMAGE_REPO ?= dev-signal-repo
IMAGE_TAG  ?= latest
BUCKET     ?= shir-dev-signal-agent
IMAGE      := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(IMAGE_REPO)/agent:$(IMAGE_TAG)
ENV_VARS   := "GOOGLE_CLOUD_PROJECT=$(PROJECT_ID),GOOGLE_CLOUD_LOCATION=$(LOCATION),GOOGLE_GENAI_USE_VERTEXAI=True,LOGS_BUCKET_NAME=$(BUCKET),AI_ASSETS_BUCKET=$(BUCKET)"

# Deploy via source (Cloud Run automated build)
deploy:
	gcloud beta run deploy dev-signal \
		--source . \
		--project $(PROJECT_ID) \
		--region $(REGION) \
		--set-env-vars $(ENV_VARS) \
		--memory "4Gi" \
		--no-allow-unauthenticated \
		--no-cpu-throttling \
		--update-build-env-vars "AGENT_VERSION=$(shell awk -F'"' '/^version = / {print $$2}' pyproject.toml || echo '0.0.0')" \
		$(if $(IAP),--iap) \
		$(if $(PORT),--port=$(PORT))

# Deploy via Cloud Build & Container (Standard for CI/CD)
docker-deploy:
	@echo "🚀 Building and deploying to $(PROJECT_ID) via Cloud Build..."
	gcloud builds submit --tag $(IMAGE) --project $(PROJECT_ID) .
	gcloud run services update dev-signal-agent \
		--image $(IMAGE) \
		--region $(REGION) \
		--project $(PROJECT_ID) \
		--set-env-vars $(ENV_VARS)

# ==============================================================================
# Infrastructure Setup
# ==============================================================================

# Set up development environment resources using Terraform
setup-dev-env:
	PROJECT_ID=$$(gcloud config get-value project) && \
	(cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve)

# ==============================================================================
# Testing & Code Quality
# ==============================================================================

# Run unit and integration tests
test:
	uv sync --dev
	uv run pytest tests/unit && uv run pytest tests/integration

# Run code quality checks (codespell, ruff, ty)
lint:
	uv sync --dev --extra lint
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run ty check .
