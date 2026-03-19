#!/bin/bash
#

. ./env.sh

set -x

# Create a regional GKE Standard cluster
gcloud container clusters create ${CLUSTER_NAME} \
    --project=${PROJECT_ID} \
    --location=${REGION} \
    --release-channel=rapid \
    --machine-type=e2-standard-4 \
    --network=${GVNIC_NETWORK_PREFIX}-main \
    --subnetwork=${GVNIC_NETWORK_PREFIX}-tpu \
    --num-nodes=1 \
    --gateway-api=standard \
    --enable-managed-prometheus \
    --enable-dataplane-v2 \
    --enable-dataplane-v2-metrics \
    --workload-pool=${PROJECT_ID}.svc.id.goog \
    --addons=GcsFuseCsiDriver,RayOperator \
    --enable-ip-alias

gcloud container clusters get-credentials ${CLUSTER_NAME} --region=${REGION}

helm install lws oci://registry.k8s.io/lws/charts/lws \
    --version=0.7.0 \
    --namespace lws-system \
    --create-namespace \
    --wait

kubectl create secret generic hf-secret \
    --from-literal=hf_api_token=${HF_TOKEN} \
    --dry-run=client -o yaml | kubectl apply -f -

gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-gkenode.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"

set +x
