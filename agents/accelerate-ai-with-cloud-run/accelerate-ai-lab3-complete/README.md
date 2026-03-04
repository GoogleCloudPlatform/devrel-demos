# Lab 3: Prototype to Production - Deploy Your ADK Agent to Cloud Run with GPU

Welcome to the final lab in the "Accelerate with AI" series! In this lab, you'll complete the prototype-to-production journey by taking a working ADK agent and deploying it as a scalable, robust application on Google Cloud Run with GPU support.

## 🎯 Learning Objectives

By the end of this lab, you will:

- Understand how to containerize ADK agents using Docker
- Deploy containerized agents to Cloud Run with GPU acceleration
- Manage production configurations and environment variables
- Test and monitor live applications in production
- Apply load testing to validate performance and scalability

## 🏗️ What You'll Build

You'll deploy a **Production Gemma Agent** with conversational capabilities:

**Gemma Agent** (GPU-Accelerated):

- General conversations and Q&A
- Educational explanations
- Creative writing assistance
- GPU-accelerated inference for fast responses
- Production-ready deployment on Cloud Run

## 📋 Prerequisites

- Google Cloud Project with billing enabled
- Google Cloud SDK installed and configured
- Docker installed (optional, for local testing)
- Basic understanding of containers and cloud deployment

## 🚀 Lab Overview

### Part 1: Understanding the Production Agent (10 minutes)

Let's first explore the agent we'll be deploying:

#### Agent Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Request  │ -> │   ADK Agent     │ -> │  Gemma Backend  │
│                 │    │  (Cloud Run)    │    │ (Cloud Run+GPU) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              v
                       ┌─────────────────┐
                       │ FastAPI Server  │
                       │ Health Checks   │
                       │ Load Testing    │
                       └─────────────────┘
```

#### Key Components

**Ollama Backend (separate deployment):**

- **`ollama-backend/Dockerfile`**: Container configuration for Gemma model backend

**ADK Agent (separate deployment):**

- **`adk-agent/production_agent/agent.py`**: Production Gemma agent with conversational capabilities
- **`adk-agent/server.py`**: FastAPI server with health checks and feedback endpoints
- **`adk-agent/Dockerfile`**: Container configuration for Cloud Run deployment
- **`adk-agent/elasticity_test.py`**: Locust-based load testing script

### Part 2: Local Development and Testing (15 minutes)

Before deploying to production, let's test the agent locally:

#### 1. Set up the Environment

```bash
# Navigate to the lab directory
cd accelerate-ai-lab3-complete/adk-agent

# Create and configure environment file
cat > .env << EOF
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=europe-west1
GEMMA_MODEL_NAME=gemma3:4b
OLLAMA_API_BASE=https://ollama-gemma-795845071313.europe-west1.run.app
EOF

# Install dependencies
uv sync
```

#### 2. Run the Agent Locally

```bash
# Start the development server
uv run python server.py
```

The agent will be available at `http://localhost:8080`. You can:

- Visit the web interface at `http://localhost:8080`
- View API documentation at `http://localhost:8080/docs`
- Test the health endpoint at `http://localhost:8080/health`

#### 3. Test Agent Capabilities

Try these sample interactions:

**With Gemma Agent** (Conversational):

- "Tell me about artificial intelligence"
- "What are some creative writing tips?"
- "Explain how photosynthesis works"
- "Can you help me brainstorm ideas for a blog post?"
- "What's the difference between machine learning and deep learning?"

### Part 3: Containerization (10 minutes)

Understanding the Dockerfile is crucial for production deployment:

```dockerfile
# Use Python 3.13 slim base image for efficiency
FROM python:3.13-slim

# Add uv package manager for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set working directory and copy files
WORKDIR /app
COPY . .

# Install Python dependencies using uv
RUN uv sync --frozen

# Expose port and start the application
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Key Production Considerations:**

- **Slim base image**: Reduces attack surface and image size
- **Package manager**: `uv` provides faster dependency resolution
- **Frozen dependencies**: Ensures reproducible builds
- **Health checks**: Built-in endpoints for monitoring

### Part 4: Deploy to Cloud Run with GPU (15 minutes)

Now let's deploy your agent to Cloud Run with GPU acceleration:

#### 1. Configure Google Cloud

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Set the region (choose one with GPU availability)
export REGION="europe-west1"
gcloud config set run/region $REGION

# Enable required APIs
gcloud services enable run.googleapis.com \
                       cloudbuild.googleapis.com \
                       aiplatform.googleapis.com
```

#### 2. Deploy to Cloud Run

```bash
# Deploy with GPU support
gcloud run deploy production-adk-agent \
    --source . \
    --region $REGION \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --gpu 1 \
    --gpu-type nvidia-l4 \
    --max-instances 3 \
    --min-instances 1 \
    --concurrency 10 \
    --timeout 300 \
    --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
    --set-env-vars GOOGLE_CLOUD_LOCATION=$REGION \
    --set-env-vars GEMMA_MODEL_NAME=gemma3:4b \
    --set-env-vars OLLAMA_API_BASE=https://ollama-gemma-795845071313.europe-west1.run.app \
    --no-cpu-throttling
```

**Deployment Configuration Explained:**

- **GPU**: NVIDIA L4 GPU for AI model acceleration
- **Memory/CPU**: Sufficient resources for AI workloads
- **Scaling**: Auto-scaling between 1-3 instances
- **Concurrency**: Handle up to 10 concurrent requests per instance
- **Environment Variables**: Production configuration

#### 3. Get Your Service URL

```bash
# Get the deployed service URL
export SERVICE_URL=$(gcloud run services describe production-adk-agent \
    --region=$REGION \
    --format='value(status.url)')

echo "🎉 Agent deployed at: $SERVICE_URL"
```

### Part 5: Testing the Live Application (10 minutes)

#### 1. Test the Deployment

```bash
# Test health endpoint
curl $SERVICE_URL/health

# Test the agent via proxy (for authenticated testing)
gcloud run services proxy production-adk-agent --port=8080
```

#### 2. Interactive Testing

With the proxy running, visit:

- Web interface: `http://localhost:8080`
- API docs: `http://localhost:8080/docs`

Try both agents' capabilities:

**Gemma Agent** (Conversational):

- "What's the difference between machine learning and deep learning?"
- "Can you help me brainstorm ideas for a blog post?"
- "Explain quantum computing in simple terms"
- "Tell me about renewable energy benefits"

### Part 6: Elasticity Testing and Performance Validation (10 minutes)

Elasticity testing ensures your agent can handle production traffic:

#### 1. Run Elasticity Tests

```bash
# Create results directory
mkdir -p .results

# Run comprehensive elasticity test
locust -f elasticity_test.py \
    -H $SERVICE_URL \
    --headless \
    -t 60s \
    -u 20 \
    -r 2 
```

**Elasticity Test Configuration:**

- **Duration**: 60 seconds
- **Users**: 20 concurrent users
- **Spawn Rate**: 2 users per second
- **Scenarios**: Gemma conversations, health checks, performance validation

**Key Metrics to Monitor:**

- **Response Time**: Should be under 10 seconds for complex queries
- **Throughput**: Requests per second handled
- **Error Rate**: Should be minimal (< 1%)
- **GPU Utilization**: Monitor in Cloud Console

## 🔧 Production Best Practices

### Environment Management

```bash
# For production deployments, use Secret Manager
gcloud secrets create production-config --data-file=.env

# Reference secrets in deployment
gcloud run deploy production-adk-agent \
    --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
    --set-secrets /app/.env=production-config:latest
```

### Monitoring and Logging

- **Cloud Logging**: Automatic logging of all agent interactions
- **Cloud Monitoring**: Set up alerts for error rates and latency
- **Cloud Trace**: Monitor request performance and bottlenecks

### Scaling Configuration

```bash
# Update scaling parameters
gcloud run services update production-adk-agent \
    --min-instances 2 \
    --max-instances 10 \
    --concurrency 5
```

## 🧪 Advanced Exercises (Optional)

1. **Custom Business Domain**: Modify the agent to specialize in your industry
2. **Multi-Model Integration**: Add different models for different tasks
3. **Caching Layer**: Implement Redis for frequently requested analyses
4. **A/B Testing**: Deploy multiple versions and compare performance

## 📊 Monitoring Your Production Agent

### Cloud Console Monitoring

1. Navigate to Cloud Run in the Google Cloud Console
2. Select your `production-adk-agent` service
3. Monitor:
   - **Metrics**: CPU, Memory, GPU utilization
   - **Logs**: Agent interactions and errors
   - **Requests**: Traffic patterns and response times

### Setting Up Alerts

```bash
# Create alerting policy for high error rates
gcloud alpha monitoring policies create \
    --policy-from-file=monitoring-policy.yaml
```

## 🎯 Key Takeaways

1. **Containerization**: Docker provides consistent deployment environments
2. **GPU Acceleration**: NVIDIA L4 GPUs significantly improve AI model performance
3. **Auto-scaling**: Cloud Run automatically scales based on demand
4. **Production Monitoring**: Comprehensive observability is essential
5. **Load Testing**: Validate performance before production traffic

## 🔍 Troubleshooting

### Common Issues

- **Cold Starts**: Use min-instances to reduce latency
- **Memory Errors**: Increase memory allocation or optimize agent code
- **GPU Unavailability**: Check regional GPU quotas and availability
- **Authentication Errors**: Verify service account permissions

### Debug Commands

```bash
# Check service status
gcloud run services describe production-adk-agent --region=$REGION

# View logs
gcloud logs read "resource.type=cloud_run_revision" --limit=50

# Test locally with production environment
uv run python server.py
```

## 🏆 Congratulations!

You've successfully completed the prototype-to-production journey! Your ADK agent is now:

- ✅ Containerized and production-ready
- ✅ Deployed on Cloud Run with GPU acceleration
- ✅ Scalable and monitored
- ✅ Load tested and validated

Your agent can now handle real business intelligence workloads and scale automatically based on demand.

## 📚 Next Steps

- Explore advanced ADK features and custom tools
- Implement CI/CD pipelines for automated deployments
- Add more sophisticated business intelligence capabilities
- Consider multi-region deployments for global availability

---

**Total Lab Time**: ~60 minutes

**Questions?** Check the troubleshooting section or review the Cloud Run documentation for additional guidance.
