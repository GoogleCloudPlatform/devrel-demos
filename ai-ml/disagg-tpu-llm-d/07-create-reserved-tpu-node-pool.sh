#!/bin/bash

. ./env.sh

set -x

for i in {1..8}
do
  gcloud beta container node-pools create "tpu-v6e-single-$i" \
    --project=n26-lp-ai-infra-screen-2 \
    --cluster=qwen-serving-cluster \
    --region=us-east5 \
    --node-locations=us-east5-a \
    --machine-type=ct6e-standard-4t \
    --tpu-topology=2x2 \
    --num-nodes=1 \
    --reservation-affinity=specific \
    --reservation=reservation-20260309-164437 \
    --workload-metadata=GKE_METADATA &
done

set +x

