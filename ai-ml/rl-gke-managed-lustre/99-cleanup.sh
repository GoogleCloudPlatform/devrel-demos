#!/bin/bash
# 99 - Cleanup script to delete the GKE cluster and Lustre instance

. ./env.sh

echo "============================================================"
echo "Cleaning up resources for RL Demo"
echo "============================================================"

echo "This will destroy the following resources:"
echo " - GKE Cluster: $CLUSTER_NAME"
echo " - Lustre Storage: $LUSTRE_INSTANCE_ID"
echo ""
read -p "Are you sure you want to proceed? (y/N) " confirm

if [[ "$confirm" =~ ^[Yy]$ ]]; then
    echo "Initiating Lustre instance deletion..."
    gcloud lustre instances delete "${LUSTRE_INSTANCE_ID}" \
        --project="${PROJECT_ID}" \
        --location="${ZONE}" \
        --quiet --async

    echo "Initiating GKE Cluster deletion via XPK..."
    xpk cluster delete \
        --project="${PROJECT_ID}" \
        --zone="${ZONE}" \
        --cluster="${CLUSTER_NAME}" \
        --force

    echo "Cleanup initiated! The resources will be taken down asynchronously."
else
    echo "Cleanup aborted."
fi
