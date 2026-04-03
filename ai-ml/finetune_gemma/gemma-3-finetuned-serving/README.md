# Deploying Fine-Tuned Gemma 3 on Cloud Run with vLLM

This directory contains the configuration to deploy a **Fine-Tuned Gemma 3 27B** model on Cloud Run. This setup uses a **LoRA adapter** stored in GCS and merges it at runtime using **vLLM** and **NVIDIA RTX 6000 Pro** GPUs.

## Prerequisites

- A Google Cloud Project with Cloud Run and Cloud Build enabled.
- Quota for `nvidia-rtx-pro-6000` GPUs.
- Fine-tuned weights (LoRA adapter) stored in `gs://shir-training-gemma3-finetuning-eu/gemma3-finetuned`.

## 1. Build the Image

The build process embeds both the **base model** (~54GB) and the **fine-tuned adapter** into the container image. This ensures the fastest possible cold starts by leveraging Cloud Run's image streaming.

```bash
export PROJECT_ID=$(gcloud config get-value project)
export HF_TOKEN=your_huggingface_token

gcloud builds submit --config cloudbuild.yaml --substitutions=_HF_TOKEN=${HF_TOKEN} .
```

## 2. Deploy to Cloud Run

Deploy the fine-tuned model as a new service.

```bash
export REGION=europe-west4
export SERVICE_NAME=gemma-3-finetuned
export IMAGE_NAME=gcr.io/${PROJECT_ID}/gemma-3-27b-finetuned-vllm:latest

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

## Cold Start & LoRA Optimization

- **Embedded Adapter**: By downloading the LoRA weights during the build process, we avoid the latency of mounting GCS FUSE or downloading weights at runtime.
- **vLLM LoRA Support**: We use the `--enable-lora` and `--lora-modules` flags. This allows vLLM to serve the base model and dynamically apply the "pet-analyzer" adapter to requests.
- **Pre-compiled Kernels**: The `torch_compile_cache` is included to skip the expensive kernel compilation step during the initial "warm-up" of the GPU instance.
