#!/bin/bash

# Function to prompt for a value if it's currently empty
prompt_if_empty() {
    local var_name=$1
    local prompt_msg=$2

    # Check if the variable is unset or empty
    if [ -z "${!var_name}" ]; then
        read -p "$prompt_msg: " input_val
        export "$var_name"="$input_val"
    fi
}

set -x
sudo apt install python3-venv
python3 -m venv ./ai-demo-venv
. ./ai-demo-venv/bin/activate

pip install -U "huggingface_hub[hf_transfer]" transformers vllm
export HF_HUB_ENABLE_HF_TRANSFER=1

curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4
chmod 700 get_helm.sh
./get_helm.sh
set +x

#Ensure we have the required values
prompt_if_empty "PROJECT_ID" "Enter your GCP Project ID"
prompt_if_empty "ZONE" "Enter your GCP Zone (e.g., us-east5-a)"
prompt_if_empty "RESERVATION_NAME" "Enter your Reservation Name"
prompt_if_empty "HF_TOKEN" "Enter your Hugging Face Token"

# Create env.sh from the template
# We use sed to replace placeholders like {{PROJECT_ID}} with actual values
cp env.sh.tmpl env.sh

sed -i "s/{{PROJECT_ID}}/$PROJECT_ID/g" env.sh
sed -i "s/{{ZONE}}/$ZONE/g" env.sh
sed -i "s/{{RESERVATION_NAME}}/$RESERVATION_NAME/g" env.sh
sed -i "s/{{HF_TOKEN}}/$HF_TOKEN/g" env.sh

echo "Configuration complete! 'env.sh' has been updated."
