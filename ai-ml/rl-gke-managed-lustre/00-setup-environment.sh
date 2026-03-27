#!/bin/bash
# Interactive setup script for the environment variables

prompt_if_empty() {
    local var_name=$1
    local prompt_msg=$2
    local default_val=$3

    if [ -z "${!var_name}" ]; then
        if [ -n "$default_val" ]; then
            read -p "$prompt_msg [$default_val]: " input_val
            input_val=${input_val:-$default_val}
        else
            read -p "$prompt_msg: " input_val
        fi
        export "$var_name"="$input_val"
    fi
}

echo "============================================================"
echo " Setting up environment configuration for RL Demo"
echo "============================================================"

# Common defaults
prompt_if_empty "PROJECT_ID" "Enter your GCP Project ID"
prompt_if_empty "ZONE" "Enter your GCP Zone" "us-east1-b"
prompt_if_empty "REGION" "Enter your GCP Region" "us-east1"
prompt_if_empty "CLUSTER_NAME" "Enter your Ray Cluster Name" "ray-a4-gpu-spot"
prompt_if_empty "LUSTRE_INSTANCE_ID" "Enter Lustre Instance ID" "rl-demo-gpu-lustre"
prompt_if_empty "LUSTRE_CAPACITY" "Enter Lustre Capacity in GiB" "9000"
prompt_if_empty "HF_TOKEN" "Enter your Hugging Face Token" ""
prompt_if_empty "WANDB_API_KEY" "Enter your WandB API Key (optional)" ""

# Node configs
prompt_if_empty "NUM_NODES" "Enter the Number of Nodes to spawn" "8"
prompt_if_empty "DEVICE_TYPE" "Enter accelerator device type" "b200-8"

echo "Copying env.sh.tmpl to env.sh and updating variables..."
cp env.sh.tmpl env.sh

# A helper to safely replace variables using sed
replace_var() {
    local var_name=$1
    local var_val="${!var_name}"
    # Escape ampersands and slashes for sed
    var_val=$(echo "$var_val" | sed -e 's/[\/&]/\\&/g')
    sed -i "s/{{${var_name}}}/$var_val/g" env.sh
}

replace_var "PROJECT_ID"
replace_var "ZONE"
replace_var "REGION"
replace_var "CLUSTER_NAME"
replace_var "LUSTRE_INSTANCE_ID"
replace_var "LUSTRE_CAPACITY"
replace_var "HF_TOKEN"
replace_var "WANDB_API_KEY"
replace_var "NUM_NODES"
replace_var "DEVICE_TYPE"

echo "Configuration complete! 'env.sh' has been updated."
echo "You can source it manually: . ./env.sh"
