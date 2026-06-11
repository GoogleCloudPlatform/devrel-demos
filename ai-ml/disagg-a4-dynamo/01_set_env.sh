#!/bin/bash
# 01_set_env.sh - Environment Setup & Configuration

set -e

ENV_FILE="env.sh"

echo "===================================================="
echo " Disaggregated Serving on A4 VMs - Env Setup"
echo "===================================================="

# Prompt for Project ID
read -p "Enter Google Cloud Project ID: " PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    echo "Error: Project ID is required."
    exit 1
fi

# Prompt for Region
read -p "Enter GCP Region [us-central1]: " REGION
REGION=${REGION:-us-central1}

# Prompt for Zone
read -p "Enter GCP Zone [us-central1-a]: " ZONE
ZONE=${ZONE:-us-central1-a}

# Prompt for GCS Bucket Name (for Anywhere Cache)
read -p "Enter GCS Bucket Name for Anywhere Cache: " BUCKET_NAME
if [ -z "$BUCKET_NAME" ]; then
    echo "Error: Bucket Name is required."
    exit 1
fi

# Prompt for Hugging Face Token
read -sp "Enter Hugging Face Token (required for downloading models): " HF_TOKEN
echo ""
if [ -z "$HF_TOKEN" ]; then
    echo "Error: Hugging Face Token is required."
    exit 1
fi

# Prompt for Model Name
read -p "Enter Model Name [meta-llama/Meta-Llama-3-8B-Instruct]: " MODEL_NAME
MODEL_NAME=${MODEL_NAME:-meta-llama/Meta-Llama-3-8B-Instruct}

# Prompt for Tokenizer Name
read -p "Enter Tokenizer Name [same as Model Name]: " TOKENIZER_NAME
TOKENIZER_NAME=${TOKENIZER_NAME:-$MODEL_NAME}

# Prompt for Reservation ID (Optional)
read -p "Enter GCP Reservation ID (leave empty if none): " RESERVATION_ID

# Prompt for Internal SSH Override (Google Corporate Network)
read -p "Use Internal SSH Override? (true/false) [true]: " USE_INTERNAL_SSH_OVERRIDE
USE_INTERNAL_SSH_OVERRIDE=${USE_INTERNAL_SSH_OVERRIDE:-true}

# Prompt for Cloud SDK Context Aware Use ECP HTTP Proxy
read -p "Cloud SDK Context Aware Use ECP HTTP Proxy? (true/false) [false]: " CLOUDSDK_CONTEXT_AWARE_USE_ECP_HTTP_PROXY
CLOUDSDK_CONTEXT_AWARE_USE_ECP_HTTP_PROXY=${CLOUDSDK_CONTEXT_AWARE_USE_ECP_HTTP_PROXY:-false}

# Define static variables
SERVED_MODEL_NAME="$MODEL_NAME"
MODEL_PATH="/data/model" # Mounted via GCS FUSE

# Save to env.sh
cat <<EOF > "$ENV_FILE"
#!/bin/bash
export PROJECT_ID="$PROJECT_ID"
export REGION="$REGION"
export ZONE="$ZONE"
export BUCKET_NAME="$BUCKET_NAME"
export HF_TOKEN="$HF_TOKEN"
export MODEL_NAME="$MODEL_NAME"
export TOKENIZER_NAME="$TOKENIZER_NAME"
export RESERVATION_ID="$RESERVATION_ID"
export SERVED_MODEL_NAME="$SERVED_MODEL_NAME"
export MODEL_PATH="$MODEL_PATH"
export USE_INTERNAL_SSH_OVERRIDE="$USE_INTERNAL_SSH_OVERRIDE"
export CLOUDSDK_CONTEXT_AWARE_USE_ECP_HTTP_PROXY=$CLOUDSDK_CONTEXT_AWARE_USE_ECP_HTTP_PROXY

# Unset proxy and cert vars that might interfere in corporate env
unset SSL_CERT_FILE REQUESTS_CA_BUNDLE PIP_CERT CURL_CA_BUNDLE GIT_SSL_CAINFO NODE_EXTRA_CA_CERTS https_proxy http_proxy HTTPS_PROXY HTTP_PROXY CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE CLOUDSDK_CONTEXT_AWARE_USE_MTLS_FOR_GRPC GOOGLE_API_CERTIFICATE_CONFIG
EOF

chmod +x "$ENV_FILE"

echo "===================================================="
echo " Configuration saved to $ENV_FILE"
echo " Please run the next script: ./02_provision_network.sh"
echo "===================================================="
