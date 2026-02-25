# Fine-tuning Gemma 3 with Cloud Run Jobs (NVIDIA RTX 6000 Pro)

This repository contains the code and configuration for fine-tuning the **Gemma 3 4B** model for Deep Image Captioning using **Cloud Run jobs** and the **NVIDIA RTX 6000 Pro (Blackwell)** GPU.

## Features
- **Serverless Fine-tuning**: Fully managed execution on Cloud Run with high-performance GPUs.
- **Deep Image Captioning**: Specialized on the [Synthetic DALL-E 3](https://huggingface.co/datasets/ProGamerGov/synthetic-dataset-1m-dalle3-high-quality-captions) dataset.
- **Memory Optimized**: Uses `Dataset.from_generator` and `low_cpu_mem_usage` for efficient streaming.
- **Modern Stack**: Leverages `uv` for dependency management and CUDA 12.8 for Blackwell compatibility.
- **Semantic Evaluation**: Uses **BERTScore** for high-fidelity caption quality assessment.

## Project Structure
- `finetune_and_evaluate.py`: Main script for fine-tuning and evaluation logic.
- `transfer_to_gcs.py`: (Optional) Script to stage the base model weights in GCS.
- `Dockerfile`: Container configuration optimized for CUDA 12.8 and Blackwell GPUs.
- `requirements.txt`: Python dependencies (includes fixes for `bitsandbytes` CUDA 12.8 binaries).

## Setup & Deployment

### 1. Environment Variables
> [!IMPORTANT]
> **Regional Alignment**: Ensure your `REGION` and `BUCKET_NAME` (storage) are in the same region (e.g., `europe-west4`) to enable GCS volume mounting.

```bash
export PROJECT_ID=[YOUR_PROJECT_ID]
export REGION=europe-west4
export HF_TOKEN=[YOUR_HF_TOKEN]
export SERVICE_ACCOUNT="gemma3-finetuner-sa"
export BUCKET_NAME=$PROJECT_ID-gemma3-finetuning-eu
export AR_REPO=gemma3-finetuning-repo
export SECRET_ID=HF_TOKEN
export IMAGE_NAME=gemma3-finetune
export JOB_NAME=gemma3-finetuning-job
```

### 2. Infrastructure Setup
```bash
# Create Service Account & Bucket
gcloud iam service-accounts create $SERVICE_ACCOUNT
gcloud storage buckets create gs://$BUCKET_NAME --location=$REGION

# Grant Permissions
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
  --member=serviceAccount:$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/storage.objectAdmin

# Store HF Token in Secret Manager
gcloud secrets create $SECRET_ID --replication-policy="automatic"
printf $HF_TOKEN | gcloud secrets versions add $SECRET_ID --data-file=-
gcloud secrets add-iam-policy-binding $SECRET_ID \
  --member serviceAccount:$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com \
  --role='roles/secretmanager.secretAccessor'
```

### 3. Staging the Model (Gemma 3 27B)
We'll use **[`cr-infer`](https://github.com/oded996/cr-infer)** to stage the model weights. Instead of installing it, you can run it directly using `uvx`.

```bash
# Download Gemma 3 27B to GCS using uvx
uvx --from git+https://github.com/oded996/cr-infer.git cr-infer model download \
  --source huggingface \
  --model-id google/gemma-3-27b-it \
  --bucket $BUCKET_NAME \
  --token $HF_TOKEN
```

### 4. Build Container (Cloud Build)
```bash
# Register AR Repo
gcloud artifacts repositories create $AR_REPO --repository-format=docker --location=$REGION

# Build
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$IMAGE_NAME:latest .
```

### 5. Create/Update Cloud Run Job
```bash
gcloud beta run jobs create $JOB_NAME \
  --region $REGION \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$IMAGE_NAME:latest \
  --set-env-vars BUCKET_NAME=$BUCKET_NAME \
  --set-secrets HF_TOKEN=$SECRET_ID:latest \
  --no-gpu-zonal-redundancy \
  --cpu 20.0 \
  --memory 80Gi \
  --task-timeout 360m \
  --gpu 1 \
  --gpu-type nvidia-rtx-pro-6000 \
  --service-account $SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com \
  --add-volume name=model-volume,type=cloud-storage,bucket=$BUCKET_NAME \
  --add-volume-mount volume=model-volume,mount-path=/mnt/gcs \
  --network=default \
  --subnet=default \
  --vpc-egress=all-traffic \
  --args="--model-id","/mnt/gcs/google/gemma-3-27b-it/","--output-dir","/tmp/gemma3-finetuned","--gcs-output-path","gs://$BUCKET_NAME/gemma3-finetuned"
```

### 4. Execute Fine-tuning
```bash
gcloud beta run jobs execute $JOB_NAME --region $REGION --async
```

## Next Steps
For production inference of your fine-tuned model, we recommend using **[`cr-infer`](https://github.com/oded996/cr-infer)** for automated deployments and smart GPU management.
