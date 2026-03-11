#!/bin/bash
# 1. Capture the commit SHA for tagging
export COMMIT_SHA=$(git rev-parse --short HEAD)
export REVISION_TAG="c-${COMMIT_SHA}"

# 2. Deploy with --no-traffic to create a Shadow Revision
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_URL" \
  --region "$REGION" \
  --no-traffic \
  --tag "${REVISION_TAG}"

# 3. Capture the unique Shadow URL for the evaluation runner
# The URL will be in the format: https://[TAG]---[SERVICE]-[HASH]-[REGION].a.run.app
export SHADOW_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.traffic[0].url)' --flatten='status.traffic' --filter="status.traffic.tag=${REVISION_TAG}")

echo "Shadow revision deployed at: $SHADOW_URL"

# 4. Promotion (to be run AFTER successful evaluation)
# gcloud run services update-traffic "$SERVICE_NAME" --region "$REGION" --to-tags "${REVISION_TAG}=100"
