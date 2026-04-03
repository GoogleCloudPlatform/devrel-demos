#!/bin/bash -x
#
EXTERNAL_IP=$(kubectl get svc vllm-tpu-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo $EXTERNAL_IP

python3 ./test_vllm.py $EXTERNAL_IP
