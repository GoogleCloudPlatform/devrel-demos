# Vision AI Demo Frontend

This is a Next.js application designed to interface with Gemma 3 models hosted on Cloud Run. It provides a clean, chat-like interface with support for image uploads and model selection.

## Features

- **GCP Native UI**: Designed with Google Cloud Console aesthetics.
- **Service Discovery**: Automatically lists available Cloud Run services in your project.
- **Secure Proxying**: Uses Application Default Credentials (ADC) to securely call authenticated Cloud Run services.
- **Local Persistence**: Conversations and settings are stored in the browser's `localStorage`.
- **Image Support**: Upload and analyze images using Gemma 3's multi-modal capabilities.

## Getting Started

### Prerequisites

- Node.js 18+ 
- Google Cloud CLI installed and authenticated (`gcloud auth application-default login`)

### Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Deployment

To deploy this application to Cloud Run using the "deploy from source" feature:

```bash
export PROJECT_ID=$(gcloud config get-value project)
export SERVICE_NAME=pet-analyzer-ui

gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region europe-west4 \
  --allow-unauthenticated
```

Cloud Run will automatically detect the `Dockerfile` in the directory, build the image using Cloud Build, and deploy the service.

## Environment Variables

- `GOOGLE_APPLICATION_CREDENTIALS`: Path to your service account key file (if not using ADC).
- `PROJECT_ID`: (Optional) The GCP Project ID if not automatically detected.
