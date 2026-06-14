#!/usr/bin/env bash
# ==============================================================================
#  Step 3: 03_setup_llm_d.sh - Setup LLM-D repo, namespace, secrets and gateway
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

echo "===================================================="
echo " Project ID: ${PROJECT_ID}"
echo " Namespace: ${NAMESPACE}"
echo " Guide Name: ${GUIDE_NAME}"
echo "===================================================="

# 1. Clone llm-d repo
if [ ! -d "llm-d" ]; then
  echo "Cloning llm-d repository..."
  export branch="main"
  git clone https://github.com/llm-d/llm-d.git
  cd llm-d
  git checkout ${branch}
  cd ..
else
  echo "llm-d directory already exists. Skipping clone."
fi

# 2. Create Namespace
echo "Creating namespace ${NAMESPACE}..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# 3. Create Hugging Face Secret
export HF_TOKEN_NAME="llm-d-hf-token"
if kubectl get secret ${HF_TOKEN_NAME} -n "${NAMESPACE}" >/dev/null 2>&1; then
  echo "Hugging Face secret ${HF_TOKEN_NAME} already exists in namespace ${NAMESPACE}. Skipping creation."
else
  echo "Creating Hugging Face secret..."
  kubectl create secret generic ${HF_TOKEN_NAME} \
      --from-literal="HF_TOKEN=${HF_TOKEN}" \
      --namespace "${NAMESPACE}" \
      --dry-run=client -o yaml | kubectl apply -f -
fi

# 4. Deploy GKE Gateway
echo "Installing Gateway API Inference Extension CRDs..."
export GAIE_VERSION="v1.5.0"
kubectl apply -k "https://github.com/kubernetes-sigs/gateway-api-inference-extension/config/crd?ref=${GAIE_VERSION}"

echo "Deploying GKE Internal Application Load Balancer..."
cd llm-d
kubectl apply -n ${NAMESPACE} -k "./guides/recipes/gateway/gke-l7-rilb"
cd ..

# 5. Wait for Gateway to be programmed
echo "Waiting for Gateway to be programmed (IP allocated)..."
echo "This may take a few minutes..."
until kubectl get gateway -n ${NAMESPACE} llm-d-inference-gateway -o jsonpath='{.status.addresses[0].value}' >/dev/null 2>&1; do
  echo -n "."
  sleep 10
done
echo ""
GATEWAY_IP=$(kubectl get gateway -n ${NAMESPACE} llm-d-inference-gateway -o jsonpath='{.status.addresses[0].value}')
echo "Gateway programmed! IP: ${GATEWAY_IP}"

# Append GATEWAY_IP to env.sh if not already there
if ! grep -q "GATEWAY_IP" env.sh; then
  echo "export GATEWAY_IP=\"${GATEWAY_IP}\"" >> env.sh
  echo "Updated env.sh with GATEWAY_IP."
fi

echo "===================================================="
echo " LLM-D setup completed successfully!"
echo " Please run: source env.sh to refresh your environment."
echo "===================================================="
