#!/bin/bash

. ./env.sh

set -x

gcloud container clusters get-credentials ${CLUSTER_NAME} --region=${REGION}

cp values_tpu.yaml llm-d/guides/pd-disaggregation/ms-pd/values_tpu.yaml
cd llm-d/guides/pd-disaggregation/
helmfile apply -e gke_tpu -n $NAMESPACE
kubectl apply -f ./httproute.gke.yaml

# Get the first Decode pod name
DECODE_POD=$(kubectl get pods -l llm-d.ai/modelservice-role=decode -o jsonpath='{.items[0].metadata.name}')

# Get the first Prefill pod name
PREFILL_POD=$(kubectl get pods -l llm-d.ai/modelservice-role=prefill -o jsonpath='{.items[0].metadata.name}')

echo "To watch the vLLM startup process, run these in separate terminals:"
echo "kubectl logs -f $DECODE_POD -c vllm"
echo "kubectl logs -f $PREFILL_POD -c vllm"

set +x
