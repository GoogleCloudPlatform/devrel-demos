#!/bin/bash
# Download the model to a local directory

. ./env.sh

set -x

hf download --local-dir=./qwen3-30b-weights \
	Qwen/Qwen3-30B-A3B

# Perform a parallel recursive upload for speed
gcloud storage cp -r ./qwen3-30b-weights gs://$BUCKET_NAME/

set +x
