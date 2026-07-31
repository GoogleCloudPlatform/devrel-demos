#!/usr/bin/env bash

SERVICE="europython-demo"
REGION="europe-central2"
SOURCE="./src"
CONFIG="./config/europython2026.env"
MAX_INSTANCE=1

gcloud run deploy $SERVICE \
  --region $REGION \
  --source $SOURCE \
  --env-vars-file $CONFIG \
  --max-instances $MAX_INSTANCE \
  --allow-unauthenticated
