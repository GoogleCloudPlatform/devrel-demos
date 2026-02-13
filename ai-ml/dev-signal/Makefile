# GCP Configuration
PROJECT_ID   := shir-training
REGION       := us-central1
SERVICE_NAME := dev-signal-v2
IMAGE_REPO   := dev-signal-v2-repo
IMAGE        := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(IMAGE_REPO)/agent:latest

# Environment overrides to bypass gcloud MTLS/ECP crashes
GCLOUD_OPTS := GOOGLE_API_CERTIFICATE_CONFIG=/dev/null \
               CLOUDSDK_PYTHON_SITEPACKAGES=1 \
               CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false \
               CLOUDSDK_ENTERPRISE_CERTIFICATE_PROXY_PATH="" \
               gcloud

# Deploy via Cloud Build & Container
docker-deploy:
	@echo "🚀 Building and deploying to $(PROJECT_ID) via Cloud Build..."
	$(GCLOUD_OPTS) builds submit --tag $(IMAGE) --project $(PROJECT_ID) .
	$(GCLOUD_OPTS) run services update $(SERVICE_NAME) \
		--image $(IMAGE) \
		--region $(REGION) \
		--project $(PROJECT_ID)

