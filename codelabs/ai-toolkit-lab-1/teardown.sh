#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 Starting Lab Teardown...${NC}"

PROJECT_ID=$(gcloud config get-value project)
REGION=${REGION:-us-central1}
CLUSTER_NAME="cymbal-bank-lab"

echo -e "${YELLOW}🗑️ Deleting GKE Autopilot cluster '$CLUSTER_NAME' in region '$REGION'...${NC}"
echo -e "${YELLOW}⏳ This will take a few minutes...${NC}"

gcloud container clusters delete "$CLUSTER_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --quiet

if [ $? -eq 0 ]; then
    echo -e "${GREEN}🎉 Cluster '$CLUSTER_NAME' deleted successfully!${NC}"
else
    echo -e "${RED}❌ Failed to delete cluster.${NC}"
fi

echo -e "${GREEN}🏁 Teardown complete.${NC}"
