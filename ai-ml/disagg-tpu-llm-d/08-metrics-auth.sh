#!/bin/bash

. ./env.sh

set -x

gcloud container clusters get-credentials ${CLUSTER_NAME} --region=${REGION}

kubectl apply -f ./metrics-auth.yaml

set +x
