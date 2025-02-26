#!/bin/bash

ECR_URL="127214177435.dkr.ecr.us-west-1.amazonaws.com/cymbalbank/"
IMAGE_TAG="latest"

# FRONTEND
FRONTEND="frontend"
FRONTEND_URL=$ECR_URL$FRONTEND:$IMAGE_TAG
echo "🐳 Building $FRONTEND_URL"
docker build --platform "linux/amd64" -t $FRONTEND_URL src/$FRONTEND
echo "⬆️ Pushing $FRONTEND_URL"
docker push $FRONTEND_URL

# # CONTACTSERVICE
CONTACTSERVICE="contacts"
CONTACTSERVICE_URL=$ECR_URL$CONTACTSERVICE:$IMAGE_TAG
echo "🐳 Building $CONTACTSERVICE_URL"
docker build --platform "linux/amd64" -t $CONTACTSERVICE_URL src/accounts/$CONTACTSERVICE
echo "⬆️ Pushing $CONTACTSERVICE_URL"
docker push $CONTACTSERVICE_URL

# # USERSERVICE
USERSERVICE="userservice"
USERSERVICE_URL=$ECR_URL$USERSERVICE:$IMAGE_TAG
echo "🐳 Building $USERSERVICE_URL"
docker build --platform linux/amd64 -t $USERSERVICE_URL src/accounts/$USERSERVICE
echo "⬆️ Pushing $USERSERVICE_URL"
docker push $USERSERVICE_URL

# BALANCEREADER
BALANCEREADER="balancereader"
BALANCEREADER_URL=$ECR_URL$BALANCEREADER:$IMAGE_TAG
echo "🐳 Building $BALANCEREADER_URL"
docker build --platform "linux/amd64" -t $BALANCEREADER_URL src/ledger/$BALANCEREADER
echo "⬆️ Pushing $BALANCEREADER_URL"
docker push $BALANCEREADER_URL

# # LEDGERWRITER
LEDGERWRITER="ledgerwriter"
LEDGERWRITER_URL=$ECR_URL$LEDGERWRITER:$IMAGE_TAG
echo "🐳 Building $LEDGERWRITER_URL"
docker build --platform "linux/amd64" -t $LEDGERWRITER_URL src/ledger/$LEDGERWRITER
echo "⬆️ Pushing $LEDGERWRITER_URL"
docker push $LEDGERWRITER_URL

# # TRANSACTIONHISTORY
TRANSACTIONHISTORY="transactionhistory"
TRANSACTIONHISTORY_URL=$ECR_URL$TRANSACTIONHISTORY:$IMAGE_TAG
echo "🐳 Building $TRANSACTIONHISTORY_URL"
docker build --platform "linux/amd64" -t $TRANSACTIONHISTORY_URL src/ledger/$TRANSACTIONHISTORY
echo "⬆️ Pushing $TRANSACTIONHISTORY_URL"
docker push $TRANSACTIONHISTORY_URL

# # LOADGENERATOR
LOADGENERATOR="loadgenerator"
LOADGENERATOR_URL=$ECR_URL$LOADGENERATOR:$IMAGE_TAG
echo "🐳 Building $LOADGENERATOR_URL"
docker build --platform "linux/amd64" -t $LOADGENERATOR_URL src/$LOADGENERATOR
echo "⬆️ Pushing $LOADGENERATOR_URL"
docker push $LOADGENERATOR_URL
