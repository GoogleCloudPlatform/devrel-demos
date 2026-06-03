#!/usr/bin/env bash
# ==============================================================================
#  Step 3: 03_install_kueue_and_slice_controller.sh - Install Orchestration Tools
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

# Setup kubectl context wrapper
kubectl() {
  if [ -n "$SERVER" ]; then
    if [ -n "$TOKEN" ]; then
      command kubectl --token="$TOKEN" --server="$SERVER" --insecure-skip-tls-verify=true "$@"
    else
      command kubectl --server="$SERVER" --insecure-skip-tls-verify=true "$@"
    fi
  else
    command kubectl "$@"
  fi
}

echo "===================================================="
# Force a newline
echo " Installing JobSet, Kueue, and GKE Slice Controller..."
echo "===================================================="

# 1. Install JobSet
# We use the versions recommended in GKE documentation
JOBSET_VER="v0.11.1"
echo "Installing JobSet (${JOBSET_VER})..."
helm upgrade --install jobset oci://registry.k8s.io/jobset/charts/jobset \
  --version "${JOBSET_VER}" \
  --namespace jobset-system \
  --create-namespace \
  --set controller.resources.requests.cpu=4 \
  --set controller.resources.requests.memory=16Gi \
  --wait

# 2. Install Kueue
KUEUE_VER="v0.16.6"
echo "Installing Kueue (${KUEUE_VER})..."
helm upgrade --install kueue oci://registry.k8s.io/kueue/charts/kueue \
  --version "${KUEUE_VER}" \
  --namespace kueue-system \
  --create-namespace \
  --set controllerManager.replicas=3 \
  --set controllerManager.manager.resources.requests.cpu=16 \
  --set controllerManager.manager.resources.requests.memory=64Gi \
  --wait

# 3. Deploy GKE Slice Controller
if [ ! -f "./slice-controller.yaml" ]; then
    echo "Error: slice-controller.yaml not found. Please ensure it was extracted."
    exit 1
fi
echo "Deploying GKE Slice Controller..."
kubectl apply -f slice-controller.yaml

# Verify Slice Controller deployment
echo "Verifying Slice Controller deployment..."
kubectl rollout status deployment/slice-controller-controller-manager -n slice-controller-system --timeout=2m

echo "===================================================="
# Force a newline
echo " JobSet, Kueue, and Slice Controller installed successfully!"
echo "===================================================="
