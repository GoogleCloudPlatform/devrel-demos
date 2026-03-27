#!/bin/bash
# 01 - Script to create a new Ray cluster using XPK

. ./env.sh

echo "============================================================"
echo "Creating new GPU Cluster: $CLUSTER_NAME"
echo "Project: $PROJECT_ID"
echo "Zone: $ZONE"
echo "Device Type: $DEVICE_TYPE"
echo "Nodes: $NUM_NODES"
echo "Using SPOT capacity (To use a reservation, remove --spot and provide the reservation flag)"
echo "============================================================"

# Submit the cluster creation request using xpk
xpk cluster create \
  --num-nodes=${NUM_NODES} \
  --device-type=${DEVICE_TYPE} \
  --default-pool-cpu-machine-type="e2-standard-4" \
  --spot \
  --enable-lustre-csi-driver \
  --project=${PROJECT_ID} \
  --zone=${ZONE} \
  --cluster=${CLUSTER_NAME}

echo "Cluster infrastructure partition creation submitted via xpk."
echo "Enabling the RayOperator Add-on..."
gcloud container clusters update ${CLUSTER_NAME} --region ${REGION} --project ${PROJECT_ID} \
  --update-addons=RayOperator=ENABLED || echo "Failed to enable RayOperator addon."
