#!/bin/bash
set -e

# Configuration
PROJECT_ID=${PROJECT_ID}
REGION=${REGION}
DB_INSTANCE="tenkai-db"
DB_NAME="tenkai"
DB_USER="tenkai"
# Generate a random password if not provided
DB_PASS=${DB_PASS:-$(openssl rand -base64 12)}
BUCKET_NAME="tenkai-artifacts-${PROJECT_ID}"
REPO_NAME="tenkai-repo"

echo "Setting up infrastructure for Project: $PROJECT_ID in Region: $REGION"

# 1. Enable APIs
echo "Enabling APIs..."
gcloud services enable run.googleapis.com \
    sqladmin.googleapis.com \
    artifactregistry.googleapis.com \
    compute.googleapis.com \
    storage.googleapis.com \
    --project "$PROJECT_ID"

# 2. Create Artifact Registry
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    echo "Creating Artifact Registry repository..."
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Tenkai Docker Repository" \
        --project="$PROJECT_ID"
else
    echo "Artifact Registry repository '$REPO_NAME' already exists."
fi

# 3. Create GCS Bucket
if ! gsutil ls -b "gs://${BUCKET_NAME}" &>/dev/null; then
    echo "Creating GCS Bucket..."
    gcloud storage buckets create "gs://${BUCKET_NAME}" --location="$REGION" --project="$PROJECT_ID"
else
    echo "GCS Bucket '$BUCKET_NAME' already exists."
fi

# 4. Create Cloud SQL Instance (Postgres)
if ! gcloud sql instances describe "$DB_INSTANCE" --project="$PROJECT_ID" &>/dev/null; then
    echo "Creating Cloud SQL Instance (this may take a while)..."
    gcloud sql instances create "$DB_INSTANCE" \
        --database-version=POSTGRES_18 \
        --tier=db-f1-micro \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --root-password="$DB_PASS" # Set root password initially
else
    echo "Cloud SQL Instance '$DB_INSTANCE' already exists."
fi

# 5. Create Database and User
echo "Configuring Database..."
# Check if DB exists
if ! gcloud sql databases list --instance="$DB_INSTANCE" --project="$PROJECT_ID" | grep -q "$DB_NAME"; then
    gcloud sql databases create "$DB_NAME" --instance="$DB_INSTANCE" --project="$PROJECT_ID"
fi
# Check if User exists
if ! gcloud sql users list --instance="$DB_INSTANCE" --project="$PROJECT_ID" | grep -q "$DB_USER"; then
    gcloud sql users create "$DB_USER" --instance="$DB_INSTANCE" --password="$DB_PASS" --project="$PROJECT_ID"
fi

echo "Setup Complete!"
echo "Database Password: $DB_PASS"
echo "Save this password for deployment!"
echo "Connection Name: $(gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID --format='value(connectionName)')"
