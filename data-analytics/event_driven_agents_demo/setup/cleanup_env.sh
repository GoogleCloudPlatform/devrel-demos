#!/bin/bash
# cleanup_env.sh
# Deletes resources created for the Event-Driven Data Agent

cd "$(dirname "$0")"

export PROJECT_ID=$(gcloud config get-value project)
export REGION="us-central1"
export DATASET_NAME="cymbal_bank"
export SA_NAME="adk-agent-sa"
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Starting cleanup for project: $PROJECT_ID in region: $REGION"

# 1. Pub/Sub
echo "Deleting Pub/Sub topic and subscription..."
gcloud pubsub subscriptions delete cymbal-bank-escalations-sub --quiet || true
gcloud pubsub topics delete cymbal-bank-escalations-topic --quiet || true

# 2. BigQuery Data & Reservations
echo "Deleting BigQuery dataset (and all tables)..."
bq rm -r -f -d ${PROJECT_ID}:${DATASET_NAME} || true

echo "Locating and deleting BigQuery Reservation Assignments..."
ASSIGNMENTS=$(bq ls --format=json --reservation_assignment --project_id=$PROJECT_ID --location=US | jq -r '.[].name' 2>/dev/null || true)
for ASSIGNMENT in $ASSIGNMENTS; do
  if [[ "$ASSIGNMENT" == *"my-continuous-reservation"* ]]; then
    ASSIGNMENT_ID=$(basename "$ASSIGNMENT")
    
    echo "Deleting assignment ID: $ASSIGNMENT_ID"
    bq rm -f --reservation_assignment --project_id=$PROJECT_ID --location=US "my-continuous-reservation.${ASSIGNMENT_ID}" || true
  fi
done

echo "Deleting BigQuery Reservation..."
bq rm -f --reservation --project_id=$PROJECT_ID --location=US my-continuous-reservation || true

# 3. Agent Engine (Reasoning Engines)
echo "Deleting deployed Reasoning Engines..."
ENGINES=$(curl -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines" | jq -r 'if .reasoningEngines then .reasoningEngines[].name else empty end')

for ENGINE in $ENGINES; do
  echo "Deleting $ENGINE..."
  curl -X DELETE -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    "https://${REGION}-aiplatform.googleapis.com/v1/$ENGINE?force=true"
  echo "Waiting for Agent Engine deletion to propagate..."
  sleep 15
done

# 4. Storage Bucket
echo "Deleting staging bucket gs://$PROJECT_ID-adk-staging..."
gcloud storage rm -r gs://$PROJECT_ID-adk-staging --quiet || true

# 5. IAM Service Account
echo "Removing IAM bindings and deleting Service Account..."
gcloud projects remove-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/aiplatform.user" --quiet || true

gcloud projects remove-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/bigquery.dataEditor" --quiet || true

gcloud iam service-accounts delete ${SA_EMAIL} --quiet || true

echo "Cleanup complete!"
