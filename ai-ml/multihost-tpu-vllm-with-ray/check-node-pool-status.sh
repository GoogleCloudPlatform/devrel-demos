# Check node pool status
gcloud container node-pools describe $NODE_POOL_NAME \
    --cluster=$CLUSTER_NAME --region=$REGION
