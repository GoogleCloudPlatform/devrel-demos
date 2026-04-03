#!/bin/bash

. ./env.sh

set -x

# Create the bucket
gcloud storage buckets create gs://$BUCKET_NAME \
    --location=$REGION \
    --uniform-bucket-level-access

#Create the Anywhere Cache for the bucket
gcloud storage buckets anywhere-caches create gs://$BUCKET_NAME $ZONE \
    --ttl=1d \
    --admission-policy=ADMIT_ON_FIRST_MISS

PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")

gsutil iam ch \
    serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com:objectViewer \
    gs://inf-demo-model-storage

set +x
