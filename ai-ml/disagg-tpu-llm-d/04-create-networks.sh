#!/bin/bash


. ./env.sh

set -x

gcloud compute --project=${PROJECT_ID} \
    networks create ${GVNIC_NETWORK_PREFIX}-main \
    --subnet-mode=auto \
    --bgp-routing-mode=regional \
    --mtu=8896

gcloud compute --project=${PROJECT_ID} \
    networks subnets create ${GVNIC_NETWORK_PREFIX}-tpu \
    --network=${GVNIC_NETWORK_PREFIX}-main \
    --region=${REGION} \
    --range=10.10.0.0/18

gcloud compute networks subnets create ${GVNIC_NETWORK_PREFIX}-proxy\
    --purpose=REGIONAL_MANAGED_PROXY \
    --role=ACTIVE \
    --region=${REGION} \
    --network=${GVNIC_NETWORK_PREFIX}-main \
    --range=172.16.0.0/26

gcloud compute --project=${PROJECT_ID} firewall-rules create ${GVNIC_NETWORK_PREFIX}-allow-icmp \
    --network=${GVNIC_NETWORK_PREFIX}-main \
    --allow=icmp \
    --source-ranges=0.0.0.0/0 \
    --description="Allow ICMP from any source." \
    --direction=INGRESS \
    --priority=1000

gcloud compute --project=${PROJECT_ID} firewall-rules create ${GVNIC_NETWORK_PREFIX}-allow-internal \
    --network=${GVNIC_NETWORK_PREFIX}-main \
    --allow=all \
    --source-ranges=172.16.0.0/12,10.0.0.0/8 \
    --description="Allow all internal traffic within the network (e.g., instance-to-instance)." \
    --direction=INGRESS \
    --priority=1000

set +x
