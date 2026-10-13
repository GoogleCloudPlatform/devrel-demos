#!/usr/bin/env bash
# ==============================================================================
#  Step 2: 02_create_cluster_and_nodes.sh - Provision VPC Networks, GKE Cluster,
#          TPU Node Pool with DRANET, and K8s Network Resources
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

# Derive region from ZONE (e.g. us-central1-ai1a -> us-central1)
REGION=$(echo "${ZONE}" | cut -d'-' -f1-2)

echo "===================================================="
echo " Project ID: ${PROJECT_ID}"
echo " Region: ${REGION}"
echo " GKE Cluster: ${CLUSTER_NAME}"
echo " Node Pool Zone: ${ZONE}"
echo " Reservation: ${RESERVATION_NAME}"
echo "===================================================="

# 0. Enable AI Zone features (visibility) for the project
echo "Enabling AI Zone visibility feature for project ${PROJECT_ID}..."
gcloud compute preview-features update ai-zones-visibility \
  --activation-status=enabled \
  --rollout-plan=fast-rollout \
  --project="${PROJECT_ID}" \
  --quiet

# Wait a few seconds for the GCE API propagation
sleep 5

# 1. Create Host VPC Network if not exists
if ! gcloud compute networks describe "${HOST_NETWORK}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating Host VPC network: ${HOST_NETWORK}..."
  gcloud compute networks create "${HOST_NETWORK}" --subnet-mode=custom --project="${PROJECT_ID}"
else
  echo "Host VPC network ${HOST_NETWORK} already exists."
fi

# Create Host Subnet if not exists
if ! gcloud compute networks subnets describe "${HOST_SUBNET}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating Host Subnet: ${HOST_SUBNET}..."
  gcloud compute networks subnets create "${HOST_SUBNET}" \
    --network="${HOST_NETWORK}" \
    --region="${REGION}" \
    --range="10.128.0.0/20" \
    --enable-private-ip-google-access \
    --project="${PROJECT_ID}"
else
  echo "Host Subnet ${HOST_SUBNET} already exists."
fi

# 3. Create GKE Cluster if not exists
# Note: Control plane runs in us-central1-a (parent of us-central1-ai1a), nodes will be zonal/regional.
if ! gcloud container clusters describe "${CLUSTER_NAME}" --region "${REGION}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating GKE Cluster ${CLUSTER_NAME} in region ${REGION}..."
  gcloud container clusters create "${CLUSTER_NAME}" \
    --region "${REGION}" \
    --num-nodes 1 \
    --machine-type="e2-standard-4" \
    --network "${HOST_NETWORK}" \
    --subnetwork "${HOST_SUBNET}" \
    --enable-ip-alias \
    --enable-dataplane-v2 \
    --workload-pool="${PROJECT_ID}.svc.id.goog" \
    --enable-multi-networking \
    --enable-private-nodes \
    --enable-private-endpoint \
    --master-ipv4-cidr="172.16.0.0/28" \
    --enable-master-authorized-networks \
    --enable-authorized-networks-on-private-endpoint \
    --release-channel=rapid \
    --addons=GcsFuseCsiDriver \
    --project "${PROJECT_ID}"
fi

# Create Firewall Rule to allow bastion-to-master communication inside VPC (port 443)
if ! gcloud compute firewall-rules describe allow-bastion-to-master --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating internal VPC firewall rule to allow bastion-to-master (port 443) ingress..."
  gcloud compute firewall-rules create allow-bastion-to-master \
    --network="${HOST_NETWORK}" \
    --direction=INGRESS \
    --allow=tcp:443 \
    --source-ranges="10.128.0.0/20" \
    --project="${PROJECT_ID}"
else
  echo "Firewall rule allow-bastion-to-master already exists."
fi

# 4. Configure kubectl credentials
echo "Configuring GKE cluster credentials..."
gcloud container clusters get-credentials "${CLUSTER_NAME}" --region "${REGION}" --project "${PROJECT_ID}"

# 6. Create GKE TPU Node Pool with DRANET
# If pool already exists, delete it first (as per template script behavior) or skip.
if gcloud container node-pools describe tpu7-gemma-pool --cluster "${CLUSTER_NAME}" --region "${REGION}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Deleting existing GKE TPU Node Pool tpu7-gemma-pool..."
  gcloud container node-pools delete tpu7-gemma-pool --cluster "${CLUSTER_NAME}" --region "${REGION}" --project "${PROJECT_ID}" --quiet
fi

echo "Creating 4-Node TPU v7 Node Pool on GKE with DRANET and Multi-NIC..."
gcloud container node-pools create tpu7-gemma-pool \
  --cluster "${CLUSTER_NAME}" \
  --region "${REGION}" \
  --node-locations "${ZONE}" \
  --machine-type "${TPU_MACHINE_TYPE}" \
  --num-nodes 4 \
  --reservation-affinity specific \
  --reservation "${RESERVATION_NAME}" \
  --accelerator-network-profile=auto \
  --node-labels=cloud.google.com/gke-networking-dra-driver=true \
  --project "${PROJECT_ID}" \
  --workload-metadata-from-node=GKE_METADATA

echo "===================================================="
echo " Node Pool successfully provisioned! Nodes list:"
echo "===================================================="
kubectl get nodes

# 7. Query GKE runtime details and append to env.sh
echo "Querying GKE private cluster endpoint..."
PRIVATE_IP=$(gcloud container clusters describe "${CLUSTER_NAME}" --region "${REGION}" --project "${PROJECT_ID}" --format="value(privateClusterConfig.privateEndpoint)")
if [ -z "$PRIVATE_IP" ]; then
  PRIVATE_IP=$(gcloud container clusters describe "${CLUSTER_NAME}" --region "${REGION}" --project "${PROJECT_ID}" --format="value(endpoint)")
fi
echo "Found GKE endpoint: ${PRIVATE_IP}"

echo "Querying GKE Node VM instance name..."
VM_NAME=$(gcloud compute instances list --filter="name~${CLUSTER_NAME}" --project "${PROJECT_ID}" --format="value(name)" | head -n 1)
echo "Found GKE Node VM instance name: ${VM_NAME}"

# Generate fresh access token
TOKEN="$(gcloud auth print-access-token)"

# Append to env.sh
cat <<EOF >> env.sh
export SERVER="https://${PRIVATE_IP}"
export NODE_VM_NAME="${VM_NAME}"
export TOKEN="${TOKEN}"
EOF

echo "===================================================="
echo " env.sh successfully updated with cluster credentials!"
echo " Please run: source env.sh to refresh your environment."
echo "===================================================="
