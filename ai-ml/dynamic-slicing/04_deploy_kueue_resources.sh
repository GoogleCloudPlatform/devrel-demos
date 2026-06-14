#!/usr/bin/env bash
# ==============================================================================
#  Step 4: 04_deploy_kueue_resources.sh - Deploy Kueue Resources
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

echo "===================================================="
# Force a newline
echo " Deploying Kueue Resources..."
echo " Namespace: ${NAMESPACE}"
echo "===================================================="

# 1. Ensure Namespace exists
echo "Creating Namespace ${NAMESPACE} if not exists..."
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# 2. Generate Kueue resources manifest from template
if [ ! -f "./kueue-resources.yaml.template" ]; then
    echo "Error: kueue-resources.yaml.template not found."
    exit 1
fi

echo "Generating kueue-resources.yaml..."
if command -v envsubst >/dev/null 2>&1; then
  envsubst < kueue-resources.yaml.template > kueue-resources.yaml
else
  echo "Warning: envsubst not found. Using sed fallback."
  sed "s/\${NAMESPACE}/${NAMESPACE}/g" kueue-resources.yaml.template > kueue-resources.yaml
fi

# 3. Apply Kueue resources
echo "Applying Kueue resources..."
kubectl apply -f kueue-resources.yaml
kubectl apply -f workload-priority-class.yaml

# 4. Verify Kueue resources
echo "Verifying Kueue resources..."
kubectl get topology slice-topology
kubectl get resourceflavor slice-rf
kubectl get admissioncheck ac
kubectl get clusterqueue cq
kubectl get localqueue lq -n "${NAMESPACE}"

echo "===================================================="
# Force a newline
echo " Kueue resources deployed successfully!"
echo "===================================================="
