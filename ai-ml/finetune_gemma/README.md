# Fine-Tuning Gemma 4 with Cloud Run Jobs

This guide explains how to fine-tune the **Gemma 4 31B** model for pet breed classification on **Cloud Run Jobs** using **NVIDIA RTX PRO 6000** GPUs.

## Prerequisites
* **Google Cloud Project** with billing enabled and APIs active (Cloud Run, Artifact Registry, Cloud Build, Secret Manager).
* **NVIDIA RTX PRO 6000** availability in your region (e.g., `europe-west4`).
* **Hugging Face Token**: A valid token with access to the Gemma 4 model weights.

## Step 0: Set Environment Variables
Set the environment variables needed for the commands below:
```bash
export PROJECT_ID=[YOUR_PROJECT_ID]
export REGION=europe-west4
export HF_TOKEN=[YOUR_HF_TOKEN]
export BUCKET_NAME=[YOUR_BUCKET_NAME]
export AR_REPO=[YOUR_AR_REPO]
export IMAGE_NAME=gemma4-finetune
```

## Step 1: Get the Code
Clone the repository and navigate to the project directory:
```bash
git clone https://github.com/GoogleCloudPlatform/devrel-demos
cd devrel-demos/ai-ml/finetune_gemma/
```

## Step 2: Stage the Model in GCS
To save startup time, stage the model weights (`google/gemma-4-31b-it`) in a GCS bucket located in the same region as your Cloud Run job.
Refer to the blog post for details on using `cr-infer` for this.

## Step 3: Build the Container
Use Cloud Build to package your script and dependencies into a container image:
```bash
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$IMAGE_NAME:latest .
```

## Step 4: Create and Execute the Cloud Run Job
Create the job with GPU support and volume mounts for the GCS bucket holding the model:
```bash
gcloud beta run jobs create gemma4-finetuning-job \
  --region $REGION \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$IMAGE_NAME:latest \
  --gpu 1 \
  --gpu-type nvidia-rtx-pro-6000 \
  --cpu 20.0 \
  --memory 80Gi \
  --add-volume name=model-volume,type=cloud-storage,bucket=$BUCKET_NAME \
  --add-volume-mount volume=model-volume,mount-path=/mnt/gcs \
  --args="--model-id","/mnt/gcs/google/gemma-4-31b-it/","--output-dir","/tmp/gemma4-finetuned","--gcs-output-path","gs://$BUCKET_NAME/gemma4-finetuned"
```

Then execute it:
```bash
gcloud beta run jobs execute gemma4-finetuning-job --region $REGION --async
```
