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

echo "===================================================="
# Force a newline
echo " Installing JobSet, Kueue, LeaderWorkerSet and GKE Slice Controller..."
echo "===================================================="

# 1. Install JobSet
# We use the versions recommended in GKE documentation
JOBSET_VER="0.11.1"
echo "Installing JobSet (${JOBSET_VER})..."
helm upgrade --install jobset oci://registry.k8s.io/jobset/charts/jobset \
  --version "${JOBSET_VER}" \
  --namespace jobset-system \
  --create-namespace \
  --wait

# 2. Install Kueue
export VERSION=v0.17.4
kubectl apply --server-side --force-conflicts -f https://github.com/kubernetes-sigs/kueue/releases/download/${VERSION}/manifests.yaml

# 3. Install LeaderWorkerSet
LWS_VERSION=v0.8.0
echo "Installing LeaderWorkerSet (${LWS_VERSION})..."
helm install lws oci://registry.k8s.io/lws/charts/lws \
    --version "${LWS_VERSION}" \
    --namespace lws-system \
    --create-namespace \
    --wait
    
echo "Deploying GKE Slice Controller..."
kubectl apply --server-side -f https://gist.githubusercontent.com/mwysokin/f8ff6a7f8c2f8808ba30177e51413e32/raw/9086457ea35cd31a3bb95b714bf72309a2be357c/kueue-slice-controller-v0.8.0-200.yaml

# Verify Slice Controller deployment
echo "Verifying Slice Controller deployment..."
kubectl rollout status deployment/slice-controller-controller-manager -n slice-controller-system --timeout=2m

echo "===================================================="
# Force a newline
echo " JobSet, Kueue, LeaderWorkerSet and Slice Controller installed successfully!"
echo "===================================================="
