#!/bin/bash
# 04_setup_infrastructure.sh - Setup etcd and NATS on Node 0

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run ./01_set_env.sh first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Setting up etcd and NATS on disagg-node-0..."
echo " Project: $PROJECT_ID"
echo " Zone: $ZONE"
echo "===================================================="



# Get internal IP of Node 0
echo "Retrieving internal IP of disagg-node-0..."
NODE_0_IP=$(gcloud compute instances describe disagg-node-0 \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].networkIP)' \
    --project="$PROJECT_ID")

echo "Node 0 Internal IP: $NODE_0_IP"

# Update env.sh with HEAD_NODE_IP for subsequent scripts
# Remove old definitions if they exist to ensure fresh update (cross-platform POSIX compatible)
if [ -f env.sh ]; then
    grep -v -E 'HEAD_NODE_IP|ETCD_ENDPOINTS|NATS_SERVER' env.sh > env.sh.tmp || true
    mv env.sh.tmp env.sh
fi

# Append fresh definitions
echo "export HEAD_NODE_IP=\"$NODE_0_IP\"" >> env.sh
echo "export ETCD_ENDPOINTS=\"http://\${HEAD_NODE_IP}:2379\"" >> env.sh
echo "export NATS_SERVER=\"nats://\${HEAD_NODE_IP}:4222\"" >> env.sh

# Commands to run on Node 0 via SSH
# We use quay.io/coreos/etcd for etcd and library/nats for NATS
SSH_COMMANDS=$(cat <<EOF
set -ex

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker not found, installing..."
    sudo apt-get update
    sudo apt-get install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# Clean up existing containers if any
sudo docker rm -f etcd nats || true

# Run etcd
# Listen on 0.0.0.0 but advertise the internal IP
sudo docker run -d \
    --name etcd \
    --net=host \
    quay.io/coreos/etcd:v3.5.0 \
    /usr/local/bin/etcd \
    --advertise-client-urls http://${NODE_0_IP}:2379 \
    --listen-client-urls http://0.0.0.0:2379

# Run NATS with JetStream enabled
sudo docker run -d \
    --name nats \
    --net=host \
    nats:latest -js

# Verify they are running
sudo docker ps

EOF
)

# Build conditional SSH arguments for corporate environment compliance
SSH_ARGS=""
if [ "$USE_INTERNAL_SSH_OVERRIDE" = "true" ]; then
    echo "Enabling Google Corporate Internal SSH Hostname override..."
    SSH_ARGS="-- -o Hostname=nic0.disagg-node-0.${ZONE}.c.${PROJECT_ID}.internal.gcpnode.com"
fi

echo "SSHing into disagg-node-0 to start services..."
gcloud compute ssh disagg-node-0 \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --command="$SSH_COMMANDS" \
    $SSH_ARGS

echo "===================================================="
echo " etcd and NATS are running on disagg-node-0."
echo " Please run the next script: ./05_deploy_prefill.sh"
echo "===================================================="
