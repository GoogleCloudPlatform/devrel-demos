# Deploying Qwen3-32B on Disaggregated v6e TPUs with llm-d and GKE

This repository provides a step-by-step guide to deploying the Qwen3-32B model on Google Cloud's v6e TPUs. The deployment leverages `llm-d` for disaggregated serving, a tiered KV cache using GCS FUSE, and the GKE inference gateway for intelligent routing.

## Features

- **Disaggregated Serving:** Separates the model weights from the TPU workers, allowing for more efficient resource utilization.
- **Tiered KV Cache:** Uses a combination of in-memory and GCS FUSE-based caching for faster inference.
- **GKE Inference Gateway:** Intelligently routes inference requests to the appropriate TPU workers.
- **Automated Setup:** The deployment process is automated using a series of shell scripts.

## Prerequisites

- A Google Cloud project with billing enabled.
- The [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and authenticated.
- A user with the appropriate permissions to create and manage GKE clusters, TPUs, and GCS buckets.

## Setup

The setup process is broken down into a series of scripts that should be run in order.

1.  **Configure Environment Variables:**

    Before you begin, open `env.sh` and set the following variables for your environment:

    ```bash
    export PROJECT_ID="your-gcp-project-id"
    export REGION="your-gcp-region"
    export CLUSTER_NAME="your-gke-cluster-name"
    ```

    Then, source the environment file:

    ```bash
    source env.sh
    ```

2.  **Run the Deployment Scripts:**

    Execute the following scripts in order to deploy the model:

    ```bash
    ./01-setup-environment.sh
    ./02-create-gcs-anywhere-cache.sh
    ./03-download-qwen-model.sh
    ./04-create-networks.sh
    ./05-create-cluster.sh
    ./06-set-up-workload-identity.sh
    ./07-create-reserved-tpu-node-pool.sh
    ./08-metrics-auth.sh
    ./09-install-llm-d.sh
    ./10-deploy-llm-d.sh
    ```

## Benchmarking

To run a benchmark test against the deployed model, use the script in the `tests` directory:

```bash
./tests/run-benchmark.sh
```

## Cleanup

To avoid incurring ongoing charges, you can tear down all the resources created during the setup process by running the cleanup script:

```bash
./cleanup.sh
```
