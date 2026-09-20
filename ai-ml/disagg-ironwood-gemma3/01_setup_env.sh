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

# 1. PROJECT_ID
DEFAULT_PROJECT_ID="${PROJECT_ID}"
read -p "Enter GCP Project ID [${DEFAULT_PROJECT_ID}]: " INPUT_PROJECT_ID
export PROJECT_ID="${INPUT_PROJECT_ID:-$DEFAULT_PROJECT_ID}"

# 2. CLUSTER_NAME
DEFAULT_CLUSTER_NAME="${CLUSTER_NAME:-gemma-serving-tpu7}"
read -p "Enter GKE Cluster Name [${DEFAULT_CLUSTER_NAME}]: " INPUT_CLUSTER_NAME
export CLUSTER_NAME="${INPUT_CLUSTER_NAME:-$DEFAULT_CLUSTER_NAME}"

# 3. ZONE
DEFAULT_ZONE="${ZONE:-us-central1-ai1a}"
read -p "Enter TPU Node Pool Zone [${DEFAULT_ZONE}]: " INPUT_ZONE
export ZONE="${INPUT_ZONE:-$DEFAULT_ZONE}"

# 4. NAMESPACE
DEFAULT_NAMESPACE="${NAMESPACE:-disagg-serving}"
read -p "Enter Kubernetes Namespace [${DEFAULT_NAMESPACE}]: " INPUT_NAMESPACE
export NAMESPACE="${INPUT_NAMESPACE:-$DEFAULT_NAMESPACE}"

# 5. RESERVATION_NAME
DEFAULT_RESERVATION_NAME="${RESERVATION_NAME}"
read -p "Enter Cloud TPU Reservation Name [${DEFAULT_RESERVATION_NAME}]: " INPUT_RESERVATION_NAME
export RESERVATION_NAME="${INPUT_RESERVATION_NAME:-$DEFAULT_RESERVATION_NAME}"

# 6. SERVED_MODEL_NAME
DEFAULT_SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-google/gemma-3-27b-it}"
read -p "Enter Model Name [${DEFAULT_SERVED_MODEL_NAME}]: " INPUT_SERVED_MODEL_NAME
export SERVED_MODEL_NAME="${INPUT_SERVED_MODEL_NAME:-$DEFAULT_SERVED_MODEL_NAME}"

# 7. GCS_BUCKET_NAME
DEFAULT_GCS_BUCKET_NAME="${GCS_BUCKET_NAME:-gemma3-weights}"
read -p "Enter GCS Bucket Name for Weights [${DEFAULT_GCS_BUCKET_NAME}]: " INPUT_GCS_BUCKET_NAME
export GCS_BUCKET_NAME="${INPUT_GCS_BUCKET_NAME:-$DEFAULT_GCS_BUCKET_NAME}"

# 8. TPU_MACHINE_TYPE
DEFAULT_TPU_MACHINE_TYPE="${TPU_MACHINE_TYPE:-tpu7x-standard-4t}"
read -p "Enter TPU Machine Type [${DEFAULT_TPU_MACHINE_TYPE}]: " INPUT_TPU_MACHINE_TYPE
export TPU_MACHINE_TYPE="${INPUT_TPU_MACHINE_TYPE:-$DEFAULT_TPU_MACHINE_TYPE}"

# 9. PREFILL_REPLICAS
DEFAULT_PREFILL_REPLICAS="${PREFILL_REPLICAS:-2}"
read -p "Enter Prefill Replicas [${DEFAULT_PREFILL_REPLICAS}]: " INPUT_PREFILL_REPLICAS
export PREFILL_REPLICAS="${INPUT_PREFILL_REPLICAS:-$DEFAULT_PREFILL_REPLICAS}"

# 10. DECODE_REPLICAS
DEFAULT_DECODE_REPLICAS="${DECODE_REPLICAS:-2}"
read -p "Enter Decode Replicas [${DEFAULT_DECODE_REPLICAS}]: " INPUT_DECODE_REPLICAS
export DECODE_REPLICAS="${INPUT_DECODE_REPLICAS:-$DEFAULT_DECODE_REPLICAS}"

# 11. HOST_NETWORK
DEFAULT_HOST_NETWORK="${HOST_NETWORK:-gemma-host-net}"
read -p "Enter VPC Host Network [${DEFAULT_HOST_NETWORK}]: " INPUT_HOST_NETWORK
export HOST_NETWORK="${INPUT_HOST_NETWORK:-$DEFAULT_HOST_NETWORK}"

# 12. HOST_SUBNET
DEFAULT_HOST_SUBNET="${HOST_SUBNET:-gemma-host-subnet}"
read -p "Enter VPC Host Subnet [${DEFAULT_HOST_SUBNET}]: " INPUT_HOST_SUBNET
export HOST_SUBNET="${INPUT_HOST_SUBNET:-$DEFAULT_HOST_SUBNET}"

# 13. HF_TOKEN (Masked Input)
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
export CLUSTER_NAME="${CLUSTER_NAME}"
export ZONE="${ZONE}"
export NAMESPACE="${NAMESPACE}"
export RESERVATION_NAME="${RESERVATION_NAME}"
export SERVED_MODEL_NAME="${SERVED_MODEL_NAME}"
export GCS_BUCKET_NAME="${GCS_BUCKET_NAME}"
export TPU_MACHINE_TYPE="${TPU_MACHINE_TYPE}"
export PREFILL_REPLICAS=${PREFILL_REPLICAS}
export DECODE_REPLICAS=${DECODE_REPLICAS}
export HF_TOKEN="${HF_TOKEN}"
export HOST_NETWORK="${HOST_NETWORK}"
export HOST_SUBNET="${HOST_SUBNET}"
EOF

echo ""
echo "===================================================="
echo " Disaggregated Environment successfully configured inside env.sh!"
echo " Please run: source env.sh to apply the configurations."
echo "===================================================="
