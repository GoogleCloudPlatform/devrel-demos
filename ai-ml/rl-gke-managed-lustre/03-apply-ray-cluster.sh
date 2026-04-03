#!/bin/bash
# 03 - Script to apply the Lustre Volumes and RayCluster Custom Resource Definition

. ./env.sh

echo "============================================================"
echo "Applying Ray Cluster and Storage Infrastructure"
echo "============================================================"

# Switch to the correct K8s context just in case
gcloud container clusters get-credentials ${CLUSTER_NAME} --region ${REGION} --project ${PROJECT_ID}

echo "Generating yaml configs from templates..."

if [ -z "${LUSTRE_IP}" ]; then
    echo "Fetching active Lustre IP dynamically..."
    export LUSTRE_IP=$(gcloud lustre instances describe "${LUSTRE_INSTANCE_ID}" --project="${PROJECT_ID}" --location="${ZONE}" --format="value(mountPoint)" | cut -d'@' -f1)
    echo "Found Lustre IP: ${LUSTRE_IP}"
fi

# Using envsubst to safely fill variables into the templates
envsubst < rl-demo-gpu-lustre.yaml.tmpl > /tmp/rl-demo-gpu-lustre.yaml
envsubst < ray_cluster_gpu.yaml.tmpl > /tmp/ray_cluster_gpu.yaml

echo "Applying Lustre PV and PVC..."
kubectl apply -f /tmp/rl-demo-gpu-lustre.yaml

echo "Applying Ray Cluster..."
kubectl apply -f /tmp/ray_cluster_gpu.yaml

echo "Configuration applied successfully."
echo "You can monitor the creation of the pods with:"
echo "kubectl get pods -w"
