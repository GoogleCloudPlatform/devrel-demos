# Deploy Ollama to Cloud Run on GPU/CPU

## Pre-requisites

Enable the following API:

- Artifact Registry API
- Cloud Build API

If you want to use GPU, check the supported region in [this link](https://cloud.google.com/run/docs/locations) and select the appropriate region. You also need to request for Cloud Run L4 quota increase as it is different with custom serving L4 quota. However, if you decide to use CPU only, it's perfectly okay

## Steps

1. Prepare artifact registry if not exist yet, this used to store docker image

    ```console
    gcloud artifacts repositories create {REPOSITORY_NAME} \
    --repository-format=docker \
    --location=us-central1
    ```

2. Build the Dockerfile using cloudbuild

    ```console
    gcloud builds submit \
    --tag us-central1-docker.pkg.dev/{PROJECT_ID}/{REPOSITORY_NAME}/ollama-gemma
    ```

3. Create dedicated service account for the cloud run

    ```console
    gcloud iam service-accounts create {SERVICE_ACCOUNT_NAME} \
    --display-name="Service Account for Ollama Cloud Run service"
    ```

4. Deploy on Cloud Run

    ```console
    gcloud beta run deploy ollama-gemma \
    --image us-central1-docker.pkg.dev/{PROJECT_ID}/{REPOSITORY}/ollama-gemma \
    --concurrency 4 \
    --cpu 8 \
    --set-env-vars OLLAMA_NUM_PARALLEL=4 \
    --gpu 1 \ # Remove this params for CPU only
    --gpu-type nvidia-l4 \ # Remove this params for CPU only
    --max-instances 1 \
    --memory 32Gi \
    --no-allow-unauthenticated \
    --no-cpu-throttling \
    --service-account {OLLAMA_IDENTITY}@{PROJECT_ID}.iam.gserviceaccount.com \
    --timeout=600
    ```
