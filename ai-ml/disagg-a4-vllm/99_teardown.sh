#!/bin/bash
# 99_teardown.sh - Tear Down all Provisioned Cluster Resources
# PURPOSE: Cleanly deletes all VMs, placement policies, stateless firewalls, subnets,
#          and RoCE VPC networks created during the serving setup.

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run ./01_set_env.sh first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Tearing down all provisioned cluster resources..."
echo " Project: $PROJECT_ID"
echo " Region: $REGION"
echo " Zone: $ZONE"
echo "===================================================="

# 1. Delete VM Instances
echo "Deleting VM instances..."
gcloud compute instances delete disagg-node-0 disagg-node-1 disagg-benchmark-host \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --quiet || echo "VMs might already be deleted, continuing..."

# 2. Delete Placement Policy
echo "Deleting compact placement policy..."
PLACEMENT_POLICY="disagg-placement"
gcloud compute resource-policies delete "$PLACEMENT_POLICY" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --quiet || echo "Placement policy might already be deleted, continuing..."

# 3. Delete Regional Firewall Policy Rule and Associations
echo "Deleting RoCE Firewall Policy rules and associations..."
gcloud compute network-firewall-policies associations delete \
    --firewall-policy=roce-firewall-policy \
    --firewall-policy-region="$REGION" \
    --name=roce-association \
    --project="$PROJECT_ID" \
    --quiet || echo "Firewall association might already be deleted, continuing..."

gcloud compute network-firewall-policies rules delete 1000 \
    --firewall-policy=roce-firewall-policy \
    --firewall-policy-region="$REGION" \
    --project="$PROJECT_ID" \
    --quiet || echo "Firewall rule might already be deleted, continuing..."

gcloud compute network-firewall-policies delete roce-firewall-policy \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --quiet || echo "Firewall policy might already be deleted, continuing..."

# 4. Delete RoCE Subnets
echo "Deleting RoCE subnets..."
for i in {0..7}; do
    gcloud compute networks subnets delete "roce-subnet-$i" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --quiet || echo "roce-subnet-$i might already be deleted, continuing..."
done

# 5. Delete RoCE VPC Network
echo "Deleting RoCE VPC Network..."
gcloud compute networks delete roce-network \
    --project="$PROJECT_ID" \
    --quiet || echo "roce-network might already be deleted, continuing..."

# 6. Clean up local environment configuration
echo "Cleaning up local env.sh..."
rm -f env.sh

echo "===================================================="
echo " Teardown completed successfully!"
echo "===================================================="
