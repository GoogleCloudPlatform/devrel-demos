# Fine-tuning Gemma 3 for Pet Breed Classification (NVIDIA RTX 6000 Pro)

Building state-of-the-art vision-language applications requires a powerful foundation. Imagine you are building a smart pet-care application. You need a model that can instantly identify the breed of a cat or dog from a simple photo to provide tailored nutrition advice or health alerts. 

To achieve this, you need the world-class reasoning of **[Gemma 3 27B](https://huggingface.co/google/gemma-3-27b-it)**, but you don't want to manage massive Kubernetes clusters or maintain idle 24/7 dedicated instances. You need a setup that is **reproducible, cost-effective, and container-native**.

By combining the **[NVIDIA RTX PRO 6000 Blackwell Server Edition GPUs](https://cloud.google.com/blog/products/serverless/cloud-run-supports-nvidia-rtx-6000-pro-gpus-for-ai-workloads)** on Cloud Run with the **Gemma 3 27B** model and the **uv** package manager, you can transform a complex VLM fine-tuning process into a simple, scalable batch job.

### The Problem: Scaling Multimodal Classification
Fine-tuning a 27B parameter model used to require complex orchestration. You’d have to:
1. Provision a massive VM.
2. Manually install CUDA drivers and dependencies.
3. Manage data transfers between local storage and the GPU.
4. Scale down manually to avoid burning costs.

### The Solution: Serverless Blackwell GPUs
Cloud Run Jobs solves this by allowing you to package your training logic as a container. With support for **RTX 6000 Pro (Blackwell)** GPUs, you get 48GB of VRAM in a fully managed environment. You only pay for the minutes your model is training, and everything—from model weight mounting via GCS to multi-epoch training—is handled within a single container.

In this guide, we walk through the process of fine-tuning the **Gemma 3 27B** model for **Pet Breed Classification** using the [Oxford-IIIT Pet Dataset](https://huggingface.co/datasets/timm/oxford-iiit-pet).

## Step 1 - Setting the stage: Your environment

To get started, prepare your Google Cloud environment and get the code. We'll use [uv](https://github.com/astral-sh/uv) to manage our local Python environment and speed up our Docker builds.

### Step 1.1 - Prepare your Google Cloud environment

1. Set environment variables. 

> [!IMPORTANT]
> **Regional Alignment is Critical**: To use Cloud Storage volume mounting, your GCS bucket **must** be in the same region as your Cloud Run job. We recommend using `europe-west4` (Netherlands) as it supports the new RTX 6000 Pro GPUs and ensures zero-latency access to your model weights.

```shell
export PROJECT_ID=[YOUR_PROJECT_ID]
export REGION=europe-west4
export HF_TOKEN=[YOUR_HF_TOKEN]
export SERVICE_ACCOUNT="finetune-gemma-job-sa"
export BUCKET_NAME=$PROJECT_ID-gemma3-finetuning-eu
export AR_REPO=gemma3-finetuning-repo
export SECRET_ID=HF_TOKEN
export IMAGE_NAME=gemma3-finetune
export JOB_NAME=gemma3-finetuning-job
```

### Step 1.2 - Get the code

Whether you're running locally or on the cloud, you'll need the code. After you open Cloud Shell or install your local Google Cloud CLI, you need to clone the repository. The `finetune_gemma` repository contains the `finetune_and_evaluate.py` script, a `Dockerfile`, and the `requirements.txt` file to your machine.

```shell
git clone https://github.com/GoogleCloudPlatform/devrel-demos
cd devrel-demos/ai-ml/finetune_gemma/
```

2. Set your Project and Authenticate:

```shell
gcloud config set project $PROJECT_ID
gcloud auth application-default login
```

3. Create the service account and grant storage permissions:

```shell
gcloud iam service-accounts create $SERVICE_ACCOUNT \
  --display-name="Service Account for Gemma 3 fine-tuning"

gcloud storage buckets create gs://$BUCKET_NAME --location=$REGION

gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
  --member=serviceAccount:$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/storage.objectAdmin
```

4. Create an Artifact Registry repository and store your HF Token in Secret Manager:

```shell
gcloud artifacts repositories create $AR_REPO \
    --repository-format=docker \
    --location=$REGION \
    --description="Gemma 3 finetuning repository"

# Create the secret (ignore error if it already exists)
gcloud secrets create $SECRET_ID --replication-policy="automatic" || true

printf $HF_TOKEN | gcloud secrets versions add $SECRET_ID --data-file=-

gcloud secrets add-iam-policy-binding $SECRET_ID \
  --member serviceAccount:$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com \
  --role='roles/secretmanager.secretAccessor'
```

## Step 2 - Staging the Model with `cr-infer` (Recommended)

To avoid downloading the model every time the job runs, we'll stage the **Gemma 3 27B** weights in Google Cloud Storage. We'll use **[`cr-infer`](https://github.com/oded996/cr-infer)**, which allows you to run model transfers directly via `uvx` without needing a local installation.

```shell
# Download Gemma 3 27B to GCS using uvx
uvx --from git+https://github.com/oded996/cr-infer.git cr-infer model download \
  --source huggingface \
  --model-id google/gemma-3-27b-it \
  --bucket $BUCKET_NAME \
  --token $HF_TOKEN
```

> [!TIP]
> This clones the model into `gs://$BUCKET_NAME/google/gemma-3-27b-it/`. This allows our Cloud Run job to mount the weights as a local volume, saving gigabytes of container startup time.

## Step 3 - Build and push the container image

Our `Dockerfile` leverages **uv** for fast dependency installation.

### Option A: Use Google Cloud Build (Recommended - No local Docker needed)
This is the easiest way to build your image directly in the cloud and push it to Artifact Registry. (The initial cold build typically takes **10-15 minutes** as it downloads large ML dependencies like PyTorch).

```shell
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$IMAGE_NAME:latest .
```

> [!TIP]
> You can track the real-time progress of your build in the [Cloud Build console](https://console.cloud.google.com/cloud-build/builds).

### Option B: Build locally with Docker
If you have Docker Desktop installed locally:

1. **Install uv locally** (if you haven't already):
```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Build the image**:
```shell
docker build -t $IMAGE_NAME .
```

3. **Push to AR**:
```shell
docker tag $IMAGE_NAME $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$IMAGE_NAME
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$IMAGE_NAME
```

### Step 3.1 - Test locally (Optional)
Before building the container, you can verify the script runs correctly using `uv`:
```shell
uv run --no-config finetune_and_evaluate.py --train-size 5 --eval-size 2 --device cpu
```

## Step 4 - Create and execute the Cloud Run job

Now, we harness the power of the **NVIDIA RTX 6000 Pro** Blackwell GPU. Our container is built with **CUDA 12.8** for full Blackwell/PyTorch 2.7 compatibility and uses an `ENTRYPOINT` configuration, allowing you to pass script arguments directly via the `--args` flag.

1. **Create the job**: Note the `--gpu-type nvidia-rtx-pro-6000` and `--task-timeout 360m` (6 hours) flags.

> [!TIP]
> **If the job already exists**, use `gcloud beta run jobs update` instead of `create`.

```shell
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
  --vpc-egress=private-ranges-only \
  --args="--model-id","/mnt/gcs/google/gemma-3-27b-it/","--output-dir","/tmp/gemma3-finetuned","--gcs-output-path","gs://$BUCKET_NAME/gemma3-finetuned","--train-size","1000","--eval-size","200","--learning-rate","5e-5"
```

### Understanding the Deployment Flags

To ensure a stable and production-ready environment, we use several specialized flags:

*   **`--gpu-type nvidia-rtx-pro-6000`**: Targets the NVIDIA RTX 6000 Pro (Blackwell Edition). With **48GB of VRAM**, it provides the massive overhead needed for multimodal fine-tuning.
*   **`--memory 80Gi`**: We allocate high system RAM to handle the `low_cpu_mem_usage` model loading and our memory-efficient streaming data generator.
*   **`--add-volume` & `--add-volume-mount`**: This mounts your GCS bucket as a local directory at `/mnt/gcs`. **Note**: This requires the bucket and the job to be in the same region (`europe-west4`). It allows the script to read the base model weights at data-center speeds without copying them into the container's writable layer.
*   **`--network` & `--subnet`**: Configures **Direct VPC Egress**, allowing the job to communicate securely with other resources in your VPC.
*   **`--vpc-egress=all-traffic`**: Ensures all outgoing traffic—including requests to Hugging Face—is routed through your VPC for enhanced security and monitoring.
*   **`--task-timeout 360m`**: ML training takes time! We set a 6-hour timeout to ensure the fine-tuning process isn't interrupted.

> [!TIP]
> **If you skipped Step 2**, notice we changed the `--model-id` in the `--args` to `google/gemma-3-27b-it` instead of a local path. This tells the script to pull directly from Hugging Face (though it will be slower than the GCS mount).

2. **Execute the job**:
```shell
gcloud beta run jobs execute $JOB_NAME --region $REGION --async
```

## Step 5 - Evaluate with Classification Metrics: Accuracy & F1 Score

For a precise task like pet breed classification, we need metrics that directly measure the model"s ability to categorize images into the correct breed labels. Unlike open-ended captioning, classification requires the model to produce a specific, recognizable class name.

For this project, we"ve implemented **Accuracy** and **Macro F1 Score** as our primary evaluation metrics.

### Why Accuracy and F1 Score?
By mapping the model"s text output to our set of 37 pet breeds (using the Oxford-IIIT Pet dataset), we can rigorously quantify its performance.

*   **Accuracy**: Provides a clear percentage of how often the model correctly identifies the breed.
*   **Macro F1 Score**: Ensures that the model performs well across all breeds, not just the most common ones. This is critical for detecting if the model is biased toward specific popular breeds.
*   **Label Mapping**: Our evaluation script includes robust text processing to find the correct breed name within the model"s generated response, even if it includes conversational filler.

## Step 6 - Check the results

Once the job completes, you can view the detailed logs in the Google Cloud Console. The fine-tuned model will be automatically saved to your Cloud Storage bucket `gs://$BUCKET_NAME/gemma3-finetuned`.

By leveraging the **RTX 6000 Pro** Blackwell GPUs on Cloud Run and a robust classification evaluation pipeline, you've transformed a complex VLM fine-tuning process into a scalable, repeatable, and cost-effective production workflow.

## Next Steps: Production Inference with `cr-infer`

Now that you've fine-tuned Gemma 3, the next challenge is serving it efficiently. For production-grade inference, we recommend using **[`cr-infer`](https://github.com/oded996/cr-infer)**. 

While Cloud Run standardizes the environment, `cr-infer` provides the "last mile" of AI-specific automation:
*   **Zero-Config Deployment**: Automatically configures the service with the correct Blackwell GPU flags and GCS volume mounts.
*   **Model Weight Orchestration**: Seamlessly handles pulling your fine-tuned weights from GCS into the inference service.
*   **Real-time Interaction**: Includes a built-in streaming chat engine so you can test your fine-tuned vision-language capabilities through a real UI immediately.

### Learn More
*   Explore the **[cr-infer GitHub Repository](https://github.com/oded996/cr-infer)**.
*   Check out the official **[Deploying Gemma on Cloud Run](https://cloud.google.com/run/docs/run-gemma-on-cloud-run)** guide for deep-dives into scaling configurations.


