# Deploying Gemma 3 27B on Cloud Run with vLLM

This directory contains the configuration to deploy the **Gemma 3 27B** model on Cloud Run using the **vLLM** inference engine and **NVIDIA RTX 6000 Pro** GPUs.

## Prerequisites

- A Google Cloud Project with Cloud Run and Cloud Build enabled.
- Quota for `nvidia-rtx-pro-6000` GPUs in your target region (e.g., `europe-west4`).
- A Hugging Face token with access to the Gemma 3 models.

## 1. Build the Image

The build process pre-downloads the model weights (~54GB) into the container image to ensure fast cold starts on Cloud Run.

```bash
export PROJECT_ID=$(gcloud config get-value project)
export HF_TOKEN=your_huggingface_token

gcloud builds submit --config cloudbuild.yaml --substitutions=_HF_TOKEN=${HF_TOKEN} .
```

> [!NOTE]
> The build can take up to 2 hours due to the model size and image layer compression. We use a high-CPU machine and 500GB of disk space in Cloud Build to handle this.

## 2. Deploy to Cloud Run

Once the image is built, deploy it to Cloud Run with GPU support.

```bash
export REGION=europe-west4
export SERVICE_NAME=gemma-3-27b
export IMAGE_NAME=gcr.io/${PROJECT_ID}/gemma-3-27b-vllm:latest

gcloud beta run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --region ${REGION} \
    --no-allow-unauthenticated \
    --concurrency 10 \
    --cpu 20 \
    --memory 80Gi \
    --gpu 1 \
    --gpu-type nvidia-rtx-pro-6000 \
    --no-gpu-zonal-redundancy \
    --timeout 3600 \
    --set-env-vars="HF_HUB_ENABLE_HF_TRANSFER=1"
```

## Cold Start Optimization

To achieve low-latency inference on serverless GPUs, this setup implements two key optimizations recommended in the [Cloud Run GPU Best Practices](https://docs.cloud.google.com/run/docs/configuring/jobs/gpu-best-practices):

### 1. Embedding Model Weights in the Image
While Cloud Run supports mounting GCS buckets (Cloud Storage FUSE), embedding large models directly into the container image is often the most performant choice for cold starts. 
- **Image Streaming**: Cloud Run uses advanced image streaming technology to start containers without waiting for the entire image to be downloaded. This allows vLLM to begin loading model weights almost immediately.
- **Reduced Latency**: By avoiding the overhead of network file system mounts, we ensure the fastest possible path from "zero to inference."

### 2. Pre-compiled `torch_compile_cache`
vLLM utilizes `torch.compile` to optimize GPU kernels for specific model architectures. This compilation process is computationally expensive and can add several minutes to the initial startup time (the "warm-up" phase).
- **The Solution**: We run the model once in a build environment to generate the optimized kernels, then capture the `torch_compile_cache` and embed it into the production image.
- **The Result**: At runtime, vLLM finds the pre-optimized kernels in the cache, skipping the compilation step entirely. This reduces the time-to-first-token significantly during a cold start.

## Configuration Details

- **GPU**: NVIDIA RTX 6000 Pro (96GB VRAM) is required to fit the 27B model in BF16/FP16.
- **Memory**: 80GiB of system RAM is allocated to handle the initial model loading and vLLM overhead.
- **Cold Starts**: By pre-downloading the model into the image, we leverage Cloud Run's image streaming for significantly faster startup times.
- **Optimization**: The `torch_compile_cache` is included in the image to skip kernel compilation at runtime.
