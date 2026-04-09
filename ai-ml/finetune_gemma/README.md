# Pet Analyzer: The Complete End-to-End Gemma 4 Lifecycle on Cloud Run

This repository provides a complete blueprint for the modern AI lifecycle using **Gemma 4 31B** on **Cloud Run Serverless GPUs**. It covers everything from model staging to fine-tuning and high-performance serving.

## Project Structure
- `vision-ai-app/`: Next.js web application for interacting with the models.
- `finetune_and_evaluate.py`: Main script for fine-tuning and evaluation logic.
- `Dockerfile`: Container configuration for the fine-tuning job.
- `requirements.txt`: Python dependencies.

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

## 1.5 VPC Network Setup (High Speed Model Streaming)
To enable low-latency model streaming from GCS, Cloud Run needs to use Direct VPC Egress with a subnet that has **Private Google Access** enabled.

```bash
export VPC_NETWORK=vllm-network
export VPC_SUBNET=vllm-subnet

# Create the VPC network
gcloud compute networks create $VPC_NETWORK --subnet-mode=custom

# Create the subnet with Private Google Access enabled
# This is CRITICAL for high-speed model loading from GCS
gcloud compute networks subnets create $VPC_SUBNET \
    --network=$VPC_NETWORK \
    --region=$REGION \
    --range=10.8.0.0/28 \
    --enable-private-ip-google-access
```

---

## 2. Deploy Base Model (Baseline)
Deploy the base Gemma 4 model using the Vertex AI optimized vLLM image.

```bash
gcloud beta run deploy vllm-gemma-4-31b-base \
    --image="us-docker.pkg.dev/vertex-ai/vertex-vision-model-garden-dockers/pytorch-vllm-serve:gemma4" \
    --region $REGION \
    --no-allow-unauthenticated \
    --gpu 1 \
    --gpu-type nvidia-rtx-pro-6000 \
    --no-gpu-zonal-redundancy \
    --network $VPC_NETWORK \
    --subnet $VPC_SUBNET \
    --vpc-egress all-traffic \
    --set-env-vars "MODEL_NAME=google/gemma-4-31b-it,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_REGION=$REGION" \
    --startup-probe tcpSocket.port=8080,initialDelaySeconds=240,failureThreshold=1,timeoutSeconds=240,periodSeconds=240 \
    --command "bash" \
    --args="^;^-c;vllm serve gs://$BUCKET_NAME/google/gemma-4-31b-it --served-model-name google/gemma-4-31b-it --enable-log-requests --enable-chunked-prefill --enable-prefix-caching --generation-config auto --dtype bfloat16 --quantization fp8 --kv-cache-dtype fp8 --max-num-seqs 8 --gpu-memory-utilization 0.95 --tensor-parallel-size 1 --load-format runai_streamer --port 8080 --host 0.0.0.0 --max-model-len 32767" \
    --timeout 3600
```

---

## 3. Deploy the Pet Analyzer UI
Launch the Next.js frontend to interact with your backends.

```bash
cd vision-ai-app
gcloud run deploy pet-analyzer-ui --source . --region $REGION --allow-unauthenticated
```

---

## 4. Fine-Tuning and Merging with Cloud Run Jobs
Execute the specialized fine-tuning job on a serverless GPU instance to create a LoRA adapter and merge it into a standalone model.

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

# Run the fine-tuning and merge job
gcloud beta run jobs execute gemma4-finetuning-job \
  --region $REGION \
  --args="--model-id","google/gemma-4-31b-it","--output-dir","/tmp/gemma4-merged","--gcs-output-path","gs://$BUCKET_NAME/gemma-4-31b-it-merged","--train-size","1000","--merge"
```

---

## 5. Deploy the Fine-Tuned (Merged) Model
Deploy the fine-tuned model. Note that since vLLM does not yet support Gemma 4 LoRA adapters directly, we use the merged standalone model.

```bash
gcloud beta run deploy vllm-gemma-4-31b-ft \
    --image="us-docker.pkg.dev/vertex-ai/vertex-vision-model-garden-dockers/pytorch-vllm-serve:gemma4" \
    --region $REGION \
    --no-allow-unauthenticated \
    --gpu 1 \
    --gpu-type nvidia-rtx-pro-6000 \
    --no-gpu-zonal-redundancy \
    --network $VPC_NETWORK \
    --subnet $VPC_SUBNET \
    --labels dev-tutorial=finetune-gemma \
    --vpc-egress all-traffic \
    --set-env-vars "MODEL_NAME=gemma-4-31b-it-finetuned,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_REGION=$REGION" \
    --startup-probe tcpSocket.port=8080,initialDelaySeconds=240,failureThreshold=1,timeoutSeconds=240,periodSeconds=240 \
    --command "bash" \
    --args="^;^-c;vllm serve gs://$BUCKET_NAME/gemma-4-31b-it-merged --served-model-name gemma-4-31b-it-finetuned --enable-log-requests --enable-chunked-prefill --enable-prefix-caching --generation-config auto --dtype bfloat16 --quantization fp8 --kv-cache-dtype fp8 --max-num-seqs 8 --gpu-memory-utilization 0.95 --tensor-parallel-size 1 --load-format runai_streamer --port 8080 --host 0.0.0.0 --max-model-len 32767" \
    --timeout 3600
```

---

## 6. Compare & Validate
Use the **Settings** in the Pet Analyzer UI to discover both `base` and `ft` services. Open two tabs to compare the results of the same pet image side-by-side!
