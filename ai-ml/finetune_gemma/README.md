# Pet Analyzer: The Complete End-to-End Gemma 4 Lifecycle on Cloud Run

This repository provides a complete blueprint for the modern AI lifecycle using **Gemma 4 31B** on **Cloud Run Serverless GPUs**. It covers everything from model staging to fine-tuning and high-performance serving.

---

## 1. Environment & Model Setup
Stage the base model weights in Google Cloud Storage to enable fast, zero-build deployments.

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=europe-west4
export BUCKET_NAME=$PROJECT_ID-models
export HF_TOKEN=your_huggingface_token

# Create bucket
gcloud storage buckets create gs://$BUCKET_NAME --location=$REGION

# Transfer weights from Hugging Face to GCS (Requires HF_TOKEN with model access)
export HF_TOKEN=your_huggingface_token
./hf-to-gcs/hf_to_gcs.py --model-id google/gemma-4-31b-it --bucket $BUCKET_NAME --token $HF_TOKEN
```

---

## 2. Deploy Base Model (Baseline)
Deploy the base Gemma 4 model using vLLM and GCS Fuse.

```bash
gcloud beta run deploy vllm-rtx6000-gemma4-31b-base \
    --image vllm/vllm-openai:latest \
    --region $REGION \
    --no-allow-unauthenticated \
    --concurrency 10 \
    --cpu 20 \
    --memory 80Gi \
    --gpu 1 \
    --gpu-type nvidia-rtx-pro-6000 \
    --no-gpu-zonal-redundancy \
    --timeout 3600 \
    --network default \
    --subnet default \
    --vpc-egress all-traffic \
    --add-volume name=models,type=cloud-storage,bucket=$BUCKET_NAME \
    --add-volume-mount volume=models,mount-path=/mnt/models \
    --set-env-vars="HF_HUB_ENABLE_HF_TRANSFER=1" \
    --args="--model","/mnt/models/google/gemma-4-31b-it","--load-format","runai_streamer","--gpu-memory-utilization","0.85","--max-model-len","8192","--trust-remote-code","--port","8080"
```

---

## 3. Deploy the Pet Analyzer UI
Launch the Next.js frontend to interact with your backends.

```bash
cd vision-ai-app
gcloud run deploy pet-analyzer-ui --source . --region $REGION --allow-unauthenticated
```

---

## 4. Fine-Tuning with Cloud Run Jobs
Execute the specialized fine-tuning job on a serverless GPU instance to create a LoRA adapter for pet breed identification.

### Prepare the Infrastructure
```bash
export SERVICE_ACCOUNT="finetune-gemma-job-sa"
gcloud iam service-accounts create $SERVICE_ACCOUNT
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
  --member=serviceAccount:$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/storage.objectAdmin
```

### Build & Execute the Job
```bash
# Build the trainer image
gcloud builds submit --tag gcr.io/$PROJECT_ID/gemma4-finetune .

# Run the fine-tuning job
gcloud beta run jobs execute gemma4-finetuning-job \
  --region $REGION \
  --args="--model-id","/mnt/gcs/google/gemma-4-31b-it/","--output-dir","/tmp/gemma4-finetuned","--gcs-output-path","gs://$BUCKET_NAME/gemma4-finetuned","--train-size","1000","--learning-rate","5e-5"
```

---

## 5. Deploy the Fine-Tuned Model
Deploy a second service running the same base model but with the new LoRA adapter applied.

```bash
gcloud beta run deploy vllm-rtx6000-gemma4-31b-ft \
    --image vllm/vllm-openai:latest \
    --region $REGION \
    --no-allow-unauthenticated \
    --concurrency 10 \
    --cpu 20 \
    --memory 80Gi \
    --gpu 1 \
    --gpu-type nvidia-rtx-pro-6000 \
    --no-gpu-zonal-redundancy \
    --timeout 3600 \
    --network default \
    --subnet default \
    --vpc-egress all-traffic \
    --add-volume name=models,type=cloud-storage,bucket=$BUCKET_NAME \
    --add-volume-mount volume=models,mount-path=/mnt/models \
    --add-volume name=finetune,type=cloud-storage,bucket=$BUCKET_NAME \
    --add-volume-mount volume=finetune,mount-path=/mnt/finetune \
    --set-env-vars="VLLM_CACHE_ROOT=/tmp/vllm,HF_HUB_ENABLE_HF_TRANSFER=1" \
    --args="--model","/mnt/models/google/gemma-4-31b-it","--enable-lora","--lora-modules","gemma-4-31b-it-fine-tuned=/mnt/finetune/gemma4-finetuned","--load-format","runai_streamer","--gpu-memory-utilization","0.85","--max-model-len","8192","--trust-remote-code","--port","8080"
```

---

## 6. Compare & Validate
Use the **Settings** in the Pet Analyzer UI to discover both `base` and `ft` services. Open two tabs to compare the results of the same pet image side-by-side!
