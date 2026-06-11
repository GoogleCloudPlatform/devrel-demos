#!/usr/bin/env bash
# ==============================================================================
#  Step 1: 01_setup_env.sh - Set up GCP Project, Cluster and Namespace configurations
# ==============================================================================
set -e

echo "===================================================="
echo " Gemma 3 Disaggregated Serving Environment Setup"
echo " Please configure the serving mesh parameters below."
echo " Press [ENTER] to accept the default values."
echo "===================================================="
echo ""

# 1. PROJECT_ID and PROJECT_NUMBER
DEFAULT_PROJECT_ID="${PROJECT_ID}"
DEFAULT_PROJECT_NUMBER="${PROJECT_NUMBER}"
read -p "Enter GCP Project ID [${DEFAULT_PROJECT_ID}]: " INPUT_PROJECT_ID
export PROJECT_ID="${INPUT_PROJECT_ID:-$DEFAULT_PROJECT_ID}"
read -p "Enter GCP Project Number [${DEFAULT_PROJECT_NUMBER}]: " INPUT_PROJECT_NUMBER
export PROJECT_NUMBER="${INPUT_PROJECT_NUMBER:-$DEFAULT_PROJECT_NUMBER}"

# 2. CLUSTER_NAME
DEFAULT_CLUSTER_NAME="${CLUSTER_NAME:-qwen-serving-cluster}"
read -p "Enter GKE Cluster Name [${DEFAULT_CLUSTER_NAME}]: " INPUT_CLUSTER_NAME
export CLUSTER_NAME="${INPUT_CLUSTER_NAME:-$DEFAULT_CLUSTER_NAME}"

# 3. ZONE
DEFAULT_ZONE="${ZONE:-us-central1-ai1a}"
read -p "Enter TPU Node Pool Zone [${DEFAULT_ZONE}]: " INPUT_ZONE
export ZONE="${INPUT_ZONE:-$DEFAULT_ZONE}"

# 4. NAMESPACE
DEFAULT_NAMESPACE="${NAMESPACE:-llm-d-pd-disaggregation}"
read -p "Enter Kubernetes Namespace [${DEFAULT_NAMESPACE}]: " INPUT_NAMESPACE
export NAMESPACE="${INPUT_NAMESPACE:-$DEFAULT_NAMESPACE}"

# 5. RESERVATION_NAME
DEFAULT_RESERVATION_NAME="${RESERVATION_NAME}"
read -p "Enter Cloud TPU Reservation Name [${DEFAULT_RESERVATION_NAME}]: " INPUT_RESERVATION_NAME
export RESERVATION_NAME="${INPUT_RESERVATION_NAME:-$DEFAULT_RESERVATION_NAME}"

# 5a. RESERVATION_PROJECT_ID (For shared reservations)
DEFAULT_RESERVATION_PROJECT_ID="${RESERVATION_PROJECT_ID:-$PROJECT_ID}"
read -p "Enter Reservation Project ID [${DEFAULT_RESERVATION_PROJECT_ID}]: " INPUT_RESERVATION_PROJECT_ID
export RESERVATION_PROJECT_ID="${INPUT_RESERVATION_PROJECT_ID:-$DEFAULT_RESERVATION_PROJECT_ID}"

# 5b. RESERVATION_BLOCK
DEFAULT_RESERVATION_BLOCK="${RESERVATION_BLOCK:-block-0}"
read -p "Enter Cloud TPU Reservation Block Name [${DEFAULT_RESERVATION_BLOCK}]: " INPUT_RESERVATION_BLOCK
export RESERVATION_BLOCK="${INPUT_RESERVATION_BLOCK:-$DEFAULT_RESERVATION_BLOCK}"

# 6. GVNIC_NETWORK_PREFIX
DEFAULT_GVNIC_NETWORK_PREFIX="${GVNIC_NETWORK_PREFIX:-qwen-serving}"
read -p "Enter gVNIC Network Prefix [${DEFAULT_GVNIC_NETWORK_PREFIX}]: " INPUT_GVNIC_NETWORK_PREFIX
export GVNIC_NETWORK_PREFIX="${INPUT_GVNIC_NETWORK_PREFIX:-$DEFAULT_GVNIC_NETWORK_PREFIX}"

# 7. GKE_VERSION
DEFAULT_GKE_VERSION="${GKE_VERSION:-1.36.0-gke.2459000}"
read -p "Enter GKE Version [${DEFAULT_GKE_VERSION}]: " INPUT_GKE_VERSION
export GKE_VERSION="${INPUT_GKE_VERSION:-$DEFAULT_GKE_VERSION}"

# 8. GUIDE_NAME
DEFAULT_GUIDE_NAME="${GUIDE_NAME:-pd-disaggregation}"
read -p "Enter Guide Name [${DEFAULT_GUIDE_NAME}]: " INPUT_GUIDE_NAME
export GUIDE_NAME="${INPUT_GUIDE_NAME:-$DEFAULT_GUIDE_NAME}"

# 9. MODEL_NAME
DEFAULT_MODEL_NAME="${MODEL_NAME:-Qwen/Qwen3.5-397B-A17B-FP8}"
read -p "Enter Model Name [${DEFAULT_MODEL_NAME}]: " INPUT_MODEL_NAME
export MODEL_NAME="${INPUT_MODEL_NAME:-$DEFAULT_MODEL_NAME}"

# 10. GCS_BUCKET_NAME
DEFAULT_GCS_BUCKET_NAME="${GCS_BUCKET_NAME:-gemma3-weights}"
read -p "Enter GCS Bucket Name for Weights [${DEFAULT_GCS_BUCKET_NAME}]: " INPUT_GCS_BUCKET_NAME
export GCS_BUCKET_NAME="${INPUT_GCS_BUCKET_NAME:-$DEFAULT_GCS_BUCKET_NAME}"

# 11. TPU_MACHINE_TYPE
DEFAULT_TPU_MACHINE_TYPE="${TPU_MACHINE_TYPE:-tpu7x-standard-4t}"
read -p "Enter TPU Machine Type [${DEFAULT_TPU_MACHINE_TYPE}]: " INPUT_TPU_MACHINE_TYPE
export TPU_MACHINE_TYPE="${INPUT_TPU_MACHINE_TYPE:-$DEFAULT_TPU_MACHINE_TYPE}"

# 12. HF_TOKEN (Masked Input)
DEFAULT_HF_TOKEN="${HF_TOKEN}"
if [ -n "${DEFAULT_HF_TOKEN}" ]; then
  # Mask the default token for security in display
  MASKED_TOKEN="${DEFAULT_HF_TOKEN:0:4}...${DEFAULT_HF_TOKEN: -4}"
  read -s -p "Enter Hugging Face Token (hidden) [Default: ${MASKED_TOKEN}]: " INPUT_HF_TOKEN
else
  read -s -p "Enter Hugging Face Token (hidden): " INPUT_HF_TOKEN
fi
echo "" # Force a newline after hidden input
export HF_TOKEN="${INPUT_HF_TOKEN:-$DEFAULT_HF_TOKEN}"

# Generate secure env.sh context
cat <<EOF > env.sh
export PROJECT_ID="${PROJECT_ID}"
export PROJECT_NUMBER="${PROJECT_NUMBER}"
export CLUSTER_NAME="${CLUSTER_NAME}"
export ZONE="${ZONE}"
export NAMESPACE="${NAMESPACE}"
export RESERVATION_NAME="${RESERVATION_NAME}"
export RESERVATION_PROJECT_ID="${RESERVATION_PROJECT_ID}"
export RESERVATION_BLOCK="${RESERVATION_BLOCK}"
export GVNIC_NETWORK_PREFIX="${GVNIC_NETWORK_PREFIX}"
export GKE_VERSION="${GKE_VERSION}"
export GUIDE_NAME="${GUIDE_NAME}"
export MODEL_NAME="${MODEL_NAME}"
export GCS_BUCKET_NAME="${GCS_BUCKET_NAME}"
export TPU_MACHINE_TYPE="${TPU_MACHINE_TYPE}"
export HF_TOKEN="${HF_TOKEN}"
EOF

echo ""
echo "===================================================="
echo " Disaggregated Environment successfully configured inside env.sh!"
echo " Please run: source env.sh to apply the configurations."
echo "===================================================="
