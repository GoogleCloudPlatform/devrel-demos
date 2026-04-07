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
export SERVICE_ACCOUNT="finetune-gemma-job-sa"
export BUCKET_NAME=$PROJECT_ID-gemma4-finetuning-eu
export AR_REPO=gemma4-finetuning-repo
export SECRET_ID=HF_TOKEN
export IMAGE_NAME=gemma4-finetune
export JOB_NAME=gemma4-finetuning-job
```

## Step 1: Get the Code
Clone the repository and navigate to the project directory:
```bash
git clone https://github.com/GoogleCloudPlatform/devrel-demos
cd devrel-demos/ai-ml/finetune_gemma/
```

## Step 2: Test Locally Before Cloud Deployment
Before spinning up massive GPUs in the cloud, verify your pipeline locally using a smaller model variant (like the 2B IT model) on a subset of the data. 

Activate your virtual environment (assuming you used `uv` or `venv`):
```bash
source .venv/bin/activate
```

Execute the script with a tiny dataset:
```bash
python3 finetune_and_evaluate.py \
  --model-id google/gemma-4-e2b-it \
  --device cpu \
  --train-size 20 \
  --eval-size 20 \
  --gradient-accumulation-steps 4 \
  --num-epochs 1
```

Once the training pipeline completes successfully, scale up to Cloud Run!

## Step 3: Stage the Model in GCS
To save startup time, stage the model weights (`google/gemma-4-31b-it`) in a GCS bucket located in the same region as your Cloud Run job. We use `cr-infer` to perform this transfer directly:

```bash
uvx --from git+https://github.com/oded996/cr-infer.git cr-infer model download \
  --source huggingface \
  --model-id google/gemma-4-31b-it \
  --bucket $BUCKET_NAME \
  --token $HF_TOKEN
```

## Step 4: Build the Container
Use Cloud Build to package your script and dependencies into a container image:
```bash
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$IMAGE_NAME:latest .
```

## Step 5: Create and Execute the Cloud Run Job
Create the job with GPU support and volume mounts for the GCS bucket holding the model:
```bash
gcloud beta run jobs create $JOB_NAME \
  --region $REGION \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$IMAGE_NAME:latest \
  --gpu 1 \
  --gpu-type nvidia-rtx-pro-6000 \
  --cpu 20.0 \
  --memory 80Gi \
  --labels dev-tutorial=finetune-gemma \
  --add-volume name=model-volume,type=cloud-storage,bucket=$BUCKET_NAME \
  --add-volume-mount volume=model-volume,mount-path=/mnt/gcs \
  --args="--model-id","/mnt/gcs/google/gemma-4-31b-it/","--output-dir","/tmp/gemma4-finetuned","--gcs-output-path","gs://$BUCKET_NAME/gemma4-finetuned","--train-size","700","--eval-size","200"
```

Then execute it:
```bash
gcloud beta run jobs execute $JOB_NAME --region $REGION --async
```
