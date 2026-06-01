#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Lab Setup...${NC}"

# 1. Check environment variables
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Error: Google Cloud Project ID is not set. Please set it using 'gcloud config set project <project-id>'${NC}"
    exit 1
fi
echo -e "${GREEN}ℹ️ Using Project ID: $PROJECT_ID${NC}"

REGION=${REGION:-us-central1}
echo -e "${GREEN}ℹ️ Using Region: $REGION${NC}"

# 2. Enable required APIs
echo -e "${YELLOW}🔗 Enabling required APIs...${NC}"
gcloud services enable \
    container.googleapis.com \
    generativelanguage.googleapis.com \
    cloudresourcemanager.googleapis.com \
    logging.googleapis.com
echo -e "${GREEN}✅ APIs enabled successfully.${NC}"

# 3. Check for required tools
echo -e "${YELLOW}🔍 Checking for required tools...${NC}"

# gcloud
if command -v gcloud &> /dev/null; then
    echo -e "${GREEN}✅ gcloud is installed.${NC}"
else
    echo -e "${RED}❌ gcloud is not installed. Please install it.${NC}"
fi

# gemini CLI
if command -v gemini &> /dev/null; then
    echo -e "${GREEN}✅ gemini CLI is installed.${NC}"
else
    echo -e "${YELLOW}⚠️ gemini CLI is not installed. In a real lab, this should be pre-installed in Cloud Shell.${NC}"
fi

# 4. Create GKE Autopilot Cluster
CLUSTER_NAME="cymbal-bank-lab"

if gcloud container clusters describe "$CLUSTER_NAME" --region "$REGION" --project "$PROJECT_ID" &> /dev/null; then
    echo -e "${GREEN}✅ GKE Autopilot cluster '$CLUSTER_NAME' already exists.${NC}"
else
    echo -e "${YELLOW}☸️ Creating GKE Autopilot cluster '$CLUSTER_NAME' in region '$REGION'...${NC}"
    echo -e "${YELLOW}⏳ This may take a few minutes...${NC}"
    gcloud container clusters create-auto "$CLUSTER_NAME" \
        --region "$REGION" \
        --project "$PROJECT_ID" \
        --labels dev-tutorial=airoadshow
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}🎉 GKE Autopilot cluster '$CLUSTER_NAME' created successfully!${NC}"
    else
        echo -e "${RED}❌ Failed to create cluster.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}🏁 Setup complete! Ready to start the lab.${NC}"
