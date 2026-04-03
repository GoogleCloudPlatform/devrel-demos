#!/bin/bash

. ./env.sh

set -x

# Create the TPU node pool using a reservation

gcloud beta container node-pools create tpu-v6e-32-resvd-pool \
    --project=${PROJECT_ID} \
    --cluster=${CLUSTER_NAME} \
    --region=${REGION} \
    --node-locations=${ZONE} \
    --machine-type=ct6e-standard-4t \
    --tpu-topology=4x8 \
    --num-nodes=8 \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --reservation-affinity=specific \
    --reservation=${RESERVATION_NAME} \
    --accelerator-network-profile=auto \
    --node-labels=cloud.google.com/gke-nodepool-group-name=${MULTIHOST_COLLECTION_NAME} \
    --node-labels=cloud.google.com/gke-workload-type=HIGH_AVAILABILITY \
    --node-labels=cloud.google.com/gke-networking-dra-driver=true

set +x
