PROJECT_ID ?= $(shell gcloud config get-value project)
REGION ?= us-central1
IMAGE_REPO ?= dev-signal-repo
IMAGE := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(IMAGE_REPO)/agent:latest

# Deploy via Cloud Build & Container
docker-deploy:
	 @echo "🚀 Building and deploying to $(PROJECT_ID) via Cloud Build..."
	gcloud builds submit --tag $(IMAGE) --project $(PROJECT_ID) .
	gcloud run services update dev-signal-agent \
		--image $(IMAGE) \
		--region $(REGION) \
		--project $(PROJECT_ID)
