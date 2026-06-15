#!/usr/bin/env bash
# ==============================================================================
#  Step 3: 03_create_cluster_and_nodes.sh - Provision VPC Networks, GKE Cluster,
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

# AI Zone features enabled in 02_enable_apis_and_features.sh


# 1. Create VPC network with large MTU (8896)
if ! gcloud compute networks describe "${GVNIC_NETWORK_PREFIX}-main" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating VPC network: ${GVNIC_NETWORK_PREFIX}-main..."
  gcloud compute networks create "${GVNIC_NETWORK_PREFIX}-main" \
      --subnet-mode=custom \
      --bgp-routing-mode=regional \
      --mtu=8896 \
      --project="${PROJECT_ID}"
else
  echo "VPC network ${GVNIC_NETWORK_PREFIX}-main already exists."
fi

# Create TPU subnet
if ! gcloud compute networks subnets describe "${GVNIC_NETWORK_PREFIX}-tpu" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating TPU Subnet: ${GVNIC_NETWORK_PREFIX}-tpu..."
  gcloud compute networks subnets create "${GVNIC_NETWORK_PREFIX}-tpu" \
      --network="${GVNIC_NETWORK_PREFIX}-main" \
      --region="${REGION}" \
      --range=10.10.0.0/18 \
      --enable-private-ip-google-access \
      --project="${PROJECT_ID}"
else
  echo "TPU Subnet ${GVNIC_NETWORK_PREFIX}-tpu already exists."
fi

# Create proxy-only subnet for GKE Gateway API
if ! gcloud compute networks subnets describe "${GVNIC_NETWORK_PREFIX}-proxy" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating Proxy-only Subnet: ${GVNIC_NETWORK_PREFIX}-proxy..."
  gcloud compute networks subnets create "${GVNIC_NETWORK_PREFIX}-proxy" \
      --purpose=REGIONAL_MANAGED_PROXY \
      --role=ACTIVE \
      --region="${REGION}" \
      --network="${GVNIC_NETWORK_PREFIX}-main" \
      --range=172.16.0.0/26 \
      --project="${PROJECT_ID}"
else
  echo "Proxy-only Subnet ${GVNIC_NETWORK_PREFIX}-proxy already exists."
fi

# Create Firewall Rule to allow internal communication
if ! gcloud compute firewall-rules describe "${GVNIC_NETWORK_PREFIX}-allow-internal" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating firewall rule ${GVNIC_NETWORK_PREFIX}-allow-internal..."
  gcloud compute firewall-rules create "${GVNIC_NETWORK_PREFIX}-allow-internal" \
      --network="${GVNIC_NETWORK_PREFIX}-main" \
      --allow=all \
      --source-ranges=172.16.0.0/12,10.0.0.0/8 \
      --description="Allow all internal traffic within the network." \
      --project="${PROJECT_ID}"
else
  echo "Firewall rule ${GVNIC_NETWORK_PREFIX}-allow-internal already exists."
fi

# 3. Create GKE Cluster if not exists
if ! gcloud container clusters describe "${CLUSTER_NAME}" --region "${REGION}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating GKE Cluster ${CLUSTER_NAME} in region ${REGION}..."
  gcloud container clusters create "${CLUSTER_NAME}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --release-channel=rapid \
    --cluster-version="${GKE_VERSION}" \
    --machine-type=n2-standard-32 \
    --network="${GVNIC_NETWORK_PREFIX}-main" \
    --subnetwork="${GVNIC_NETWORK_PREFIX}-tpu" \
    --num-nodes=1 \
    --gateway-api=standard \
    --enable-managed-prometheus \
    --enable-dataplane-v2 \
    --enable-dataplane-v2-metrics \
    --workload-pool="${PROJECT_ID}.svc.id.goog" \
    --enable-ip-alias \
    --addons=HttpLoadBalancing,GcpFilestoreCsiDriver,GcsFuseCsiDriver,HorizontalPodAutoscaling,NodeLocalDNS \
    --enable-slice-controller
    
  echo "Adding Maintenance Exclusion to GKE Cluster..."
  gcloud container clusters update "${CLUSTER_NAME}" \
    --location="${REGION}" \
    --add-maintenance-exclusion-name="no-upgrade-next-month" \
    --add-maintenance-exclusion-start="2026-05-18T00:00:00Z" \
    --add-maintenance-exclusion-end="2026-08-15T00:00:00Z" \
    --add-maintenance-exclusion-scope="no_upgrades" \
    --project="${PROJECT_ID}"
else
  echo "GKE Cluster ${CLUSTER_NAME} already exists."
fi


# 4. Configure kubectl credentials
echo "Configuring GKE cluster credentials..."
gcloud container clusters get-credentials "${CLUSTER_NAME}" --region "${REGION}" --project "${PROJECT_ID}"

# 5. Create Workload Policy for Dynamic Slicing
if ! gcloud compute resource-policies describe superslice-policy --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating Workload Policy superslice-policy..."
  gcloud compute resource-policies create workload-policy superslice-policy \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --type=HIGH_THROUGHPUT \
    --accelerator-topology=4x4x4 \
    --accelerator-topology-mode=provision_only
else
  echo "Workload Policy superslice-policy already exists."
fi

# 6. Create GKE TPU Node Pools with Incremental Provisioning
# We have 256 chips = 4 sub-blocks of 16 VMs.
# We target the block reservation and create 4 node pools of 16 nodes each.
if [ -z "${RESERVATION_BLOCK}" ]; then
  echo "Error: RESERVATION_BLOCK is not set in env.sh."
  exit 1
fi

# Fallback if RESERVATION_PROJECT_ID is not set in env.sh
RESERVATION_PROJECT_ID="${RESERVATION_PROJECT_ID:-$PROJECT_ID}"
RESERVATION_PATH="projects/${RESERVATION_PROJECT_ID}/reservations/${RESERVATION_NAME}/reservationBlocks/${RESERVATION_BLOCK}"
echo "Using Reservation Path: ${RESERVATION_PATH}"

for i in {1..2}; do
  POOL_NAME="tpu7-pool-${i}"
  
  # If pool already exists, we skip creation
  if gcloud container node-pools describe "${POOL_NAME}" --cluster "${CLUSTER_NAME}" --region "${REGION}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    echo "Node pool ${POOL_NAME} already exists. Skipping creation."
  else
    echo "Creating GKE TPU Node Pool ${POOL_NAME} (16 nodes)..."
    gcloud container node-pools create "${POOL_NAME}" \
      --cluster "${CLUSTER_NAME}" \
      --region "${REGION}" \
      --node-locations "${ZONE}" \
      --machine-type "${TPU_MACHINE_TYPE}" \
      --num-nodes 16 \
      --placement-policy=superslice-policy \
      --reservation-affinity specific \
      --reservation "${RESERVATION_PATH}" \
      --project "${PROJECT_ID}" \
      --workload-metadata-from-node=GKE_METADATA \
      --quiet
  fi
done

echo "===================================================="
echo " Node Pool successfully provisioned! Nodes list:"
echo "===================================================="
kubectl get nodes

# 7. Query GKE runtime details and append to env.sh
echo "Querying GKE cluster endpoint..."
CLUSTER_ENDPOINT=$(gcloud container clusters describe "${CLUSTER_NAME}" --region "${REGION}" --project "${PROJECT_ID}" --format="value(endpoint)")
echo "Found GKE endpoint: ${CLUSTER_ENDPOINT}"

echo "Querying GKE Node VM instance name..."
VM_NAME=$(gcloud compute instances list --filter="name~${CLUSTER_NAME}" --project "${PROJECT_ID}" --format="value(name)" | head -n 1)
echo "Found GKE Node VM instance name: ${VM_NAME}"

# Generate fresh access token
TOKEN="$(gcloud auth print-access-token)"

# Append to env.sh
cat <<EOF >> env.sh
export SERVER="https://${CLUSTER_ENDPOINT}"
export NODE_VM_NAME="${VM_NAME}"
export TOKEN="${TOKEN}"
EOF

echo "===================================================="
echo " env.sh successfully updated with cluster credentials!"
echo " Please run: source env.sh to refresh your environment."
echo "===================================================="
