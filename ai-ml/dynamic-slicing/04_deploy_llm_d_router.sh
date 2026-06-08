#!/usr/bin/env bash
# ==============================================================================
#  Step 4: 04_deploy_llm_d_router.sh - Deploy LLM-D Router in Gateway Mode
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

if [ ! -d "llm-d" ]; then
    echo "Error: llm-d directory not found. Please run 03_setup_llm_d.sh first."
    exit 1
fi

echo "===================================================="
echo " Project ID: ${PROJECT_ID}"
echo " Namespace: ${NAMESPACE}"
echo " Guide Name: ${GUIDE_NAME}"
echo " Model Name: ${MODEL_NAME}"
echo "===================================================="

# Deploy LLM-D Router in Gateway Mode
export ROUTER_CHART_VERSION="v0"
export REPO_ROOT="$(realpath ./llm-d)"
export PROVIDER_NAME="gke"

echo "Deploying LLM-D Router via Helm..."
helm install ${GUIDE_NAME} \
    oci://ghcr.io/llm-d/charts/llm-d-router-gateway-dev  \
    -f ${REPO_ROOT}/guides/recipes/router/base.values.yaml \
    -f ${REPO_ROOT}/guides/recipes/router/features/httproute-flags.yaml \
    -f ${REPO_ROOT}/guides/${GUIDE_NAME}/router/${GUIDE_NAME}.values.yaml \
    --set provider.name=${PROVIDER_NAME} \
    -n ${NAMESPACE} --version ${ROUTER_CHART_VERSION}

echo "Waiting for Router pods to be ready..."
kubectl wait --namespace ${NAMESPACE} \
  --for=condition=ready pod \
  --selector=llm-d.ai/igw-mode=llm-d-router-gateway \
  --timeout=300s

echo "===================================================="
echo " LLM-D Router deployed successfully!"
echo "===================================================="
