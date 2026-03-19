# Multihost TPU vLLM Inferencing with Ray on GKE

This repository provides a set of scripts and Kubernetes manifests to deploy a high-performance, multi-host vLLM (Virtual Large Language Model) inferencing service on Google Kubernetes Engine (GKE) using Google Cloud TPUs. The deployment leverages Ray for distributed computing and LeaderWorkerSets for managing the distributed workload.

## Overview

The project is structured as a series of scripts to automate the setup of the required infrastructure and the deployment of the vLLM service. The process is as follows:

1.  **Environment Setup**: Configure your local environment and Google Cloud project settings.
2.  **Infrastructure Provisioning**: Create the necessary networking, GCS buckets, and GKE cluster with a TPU node pool.
3.  **Model Download**: Download a pre-trained language model (e.g., Qwen) from Hugging Face and store it in a GCS bucket for efficient access.
4.  **Deployment**: Deploy the vLLM service on the GKE cluster using Ray and LeaderWorkerSets.
5.  **Testing and Benchmarking**: Test the deployed service and run benchmarks to evaluate its performance.

## Prerequisites

Before you begin, ensure you have the following installed and configured:

*   [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`)
*   [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
*   [Helm](https://helm.sh/docs/intro/install/)
*   A Google Cloud Project with billing enabled.
*   A project with available TPU v5e or v6e quota in your desired region.
*   A [Hugging Face](https.huggingface.co) account and an access token with permissions to download the desired models.

## Repository Structure

```
├── 01-setup-environment.sh          # Configures the environment
├── 02-create-gcs-anywhere-cache.sh  # Creates a GCS bucket for model caching
├── 03-download-qwen-model.sh        # Downloads the model to GCS
├── 04-create-networks.sh            # Sets up VPC and networking
├── 05-create-cluster.sh             # Creates the GKE cluster
├── 06-set-up-workload-identity.sh   # Configures Workload Identity
├── 07-create-reserved-tpu-node-pool.sh # Creates a reserved TPU node pool
├── cleanup.sh                       # Deletes all created resources
├── env.sh.tmpl                      # Template for environment variables
├── multihost-vllm/                  # Kubernetes manifests for vLLM
│   ├── 01-resource-claim-template.yaml
│   ├── 02-vllm-service.yaml
│   └── 03-multihost-vllm.yaml
└── tests/                           # Scripts for testing and benchmarking
    ├── benchmark.sh
    ├── benchmark_sharegpt.sh
    ├── get-bench-data.sh
    ├── test_vllm.py
    └── test-vllm.sh
```

## Step-by-Step Guide

### 1. Setup Environment

First, clone this repository to your local machine.

```bash
git clone <repository-url>
cd <repository-directory>
```

Run the `01-setup-environment.sh` script. This script will prompt you for your Google Cloud Project ID, Zone, reservation name, and Hugging Face token. It will also create a Python virtual environment and install the necessary dependencies.

```bash
./01-setup-environment.sh
```

After the script completes, it will create an `env.sh` file. Source this file to load the environment variables into your shell session. You will need to do this for every new terminal session.

```bash
source env.sh
```

### 2. Provision Infrastructure

Run the following scripts in order to provision the necessary cloud infrastructure. Each script is designed to be idempotent and will report if a resource already exists.

```bash
./02-create-gcs-anywhere-cache.sh
./03-download-qwen-model.sh
./04-create-networks.sh
./05-create-cluster.sh
./06-set-up-workload-identity.sh
./07-create-reserved-tpu-node-pool.sh
```

After creating the cluster, retrieve its credentials:
```bash
gcloud container clusters get-credentials ${CLUSTER_NAME} --zone ${ZONE}
```

You can check the status of the node pool creation with:
```bash
./check-node-pool-status.sh
```

### 3. Deploy vLLM Service

Once the GKE cluster and node pool are ready, deploy the vLLM service by applying the Kubernetes manifests in the `multihost-vllm` directory in the specified order:

```bash
kubectl apply -f multihost-vllm/01-resource-claim-template.yaml
kubectl apply -f multihost-vllm/02-vllm-service.yaml
kubectl apply -f multihost-vllm/03-multihost-vllm.yaml
```

This will deploy a `LeaderWorkerSet` that launches a Ray cluster on the TPU nodes, running the vLLM engine.

### 4. Test and Benchmark

After deploying the service, you can test it using the scripts in the `tests` directory.

To run a simple test, use the `test-vllm.sh` script. This will send a sample prompt to the vLLM service and print the response.

```bash
./tests/test-vllm.sh
```

For performance evaluation, you can use the benchmarking scripts. The `get-bench-data.sh` script downloads a dataset for benchmarking.

```bash
./tests/get-bench-data.sh
./tests/benchmark.sh
# or for ShareGPT data
./tests/benchmark_sharegpt.sh
```

### 5. Cleanup

To avoid incurring ongoing charges, you can delete all the resources created by these scripts by running the `cleanup.sh` script.

```bash
./cleanup.sh
```

This script will tear down the GKE cluster, GCS bucket, and network resources.
