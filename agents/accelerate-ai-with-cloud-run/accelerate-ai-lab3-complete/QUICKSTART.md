# 🚀 Quick Start Guide - Lab 3

Get your production ADK agent running on Cloud Run with GPU in 15 minutes!

## Prerequisites (2 minutes)

```bash
# Set your Google Cloud project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID
gcloud config set run/region europe-west1

# Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com
```

Deploy Gemma Backend

```bash
cd ollama-backend
gcloud run deploy ollama-gemma34b-gpu \
  --source . \
  --concurrency 4 \
  --cpu 8 \
  --set-env-vars OLLAMA_NUM_PARALLEL=4 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --max-instances 1 \
  --memory 32Gi \
  --allow-unauthenticated \
  --no-cpu-throttling \
  --no-gpu-zonal-redundancy \
  --timeout=600
```

## Deploy to Production (5 minutes)

```bash
# Clone and navigate to lab
cd accelerate-ai-lab3-complete/adk-agent

# Create environment file
cat > .env << EOF
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_LOCATION=europe-west1
GEMMA_MODEL_NAME=gemma3:4b
OLLAMA_API_BASE=https://ollama-gemma-795845071313.europe-west1.run.app
EOF

# Deploy with GPU support
gcloud run deploy production-adk-agent \
    --source . \
    --region europe-west1 \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --gpu 1 \
    --gpu-type nvidia-l4 \
    --max-instances 5 \
    --min-instances 1 \
    --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
    --set-env-vars GOOGLE_CLOUD_LOCATION=europe-west1 \
    --set-env-vars GEMMA_MODEL_NAME=gemma3:4b \
    --set-env-vars OLLAMA_API_BASE=https://ollama-gemma-795845071313.europe-west1.run.app
```

## Test Your Agent (3 minutes)

```bash
# Get service URL
export SERVICE_URL=$(gcloud run services describe production-adk-agent \
    --region=europe-west1 \
    --format='value(status.url)')

# Test health endpoint
curl $SERVICE_URL/health

# Start proxy for web interface
gcloud run services proxy production-adk-agent --port=8080
# Then visit: http://localhost:8080
```

## Load Test (5 minutes)

```bash
# Install and run load test
uv sync
mkdir -p .results

locust -f load_test.py \
    -H $SERVICE_URL \
    --headless \
    -t 60s -u 20 -r 2 \
    --csv=.results/results \
    --html=.results/report.html

# View results
open .results/report.html
```

## 🎉 Done!

Your production ADK agent is now running on Cloud Run with GPU acceleration!

**Try these queries:**

**Gemma Agent** (Conversational):

- "Tell me about artificial intelligence"
- "What are some creative writing tips?"
- "Explain quantum computing in simple terms"
- "Can you help me brainstorm ideas for a blog post?"
