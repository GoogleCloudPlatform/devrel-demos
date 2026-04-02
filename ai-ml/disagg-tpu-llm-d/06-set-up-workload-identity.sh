#!/bin/bash
#

. ./env.sh

set -x

gcloud container clusters get-credentials ${CLUSTER_NAME} --region=${REGION}

gcloud iam service-accounts create tpu-reader-sa

sleep 5

gcloud storage buckets add-iam-policy-binding gs://inf-demo-model-storage \
	--member="serviceAccount:tpu-reader-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
	--role="roles/storage.objectViewer"

gcloud iam service-accounts add-iam-policy-binding tpu-reader-sa@${PROJECT_ID}.iam.gserviceaccount.com \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:${PROJECT_ID}.svc.id.goog[default/default]"

kubectl annotate serviceaccount default iam.gke.io/gcp-service-account=tpu-reader-sa@${PROJECT_ID}.iam.gserviceaccount.com

set +x
