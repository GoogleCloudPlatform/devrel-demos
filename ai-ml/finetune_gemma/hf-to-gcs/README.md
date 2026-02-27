# HF to GCS Transfer Tool

A simple CLI tool to transfer Hugging Face models directly to Google Cloud Storage using Cloud Build. This is optimized for large weights, leveraging Google's network for fast transfers.

## Prerequisites

- Google Cloud CLI (`gcloud`) installed and authenticated.
- A Hugging Face account and access token with access to the requested model.

## Usage

Run the script from within this directory, providing the model ID, target bucket, and your token.

```bash
./hf_to_gcs.py --model-id google/gemma-3-27b-it --bucket my-gemma-bucket --token your_hf_token
```

Alternatively, you can set the `HF_TOKEN` environment variable:

```bash
export HF_TOKEN=your_token
./hf_to_gcs.py --model-id google/gemma-3-27b-it --bucket my-gemma-bucket
```

## How it works

The tool triggers a Cloud Build job that:
1.  **High-Speed Download**: Downloads the model from Hugging Face using the `hf_transfer` library for maximum throughput.
2.  **GCS Upload**: Efficiently uploads the model weights directly to your GCS bucket.
3.  **Organization**: Automatically organizes the files under a prefix matching the model ID (e.g., `gs://bucket/google/gemma-3-27b-it/...`).
4.  **Cost-Effective**: Only uses high-performance compute during the transfer process and scales to zero once finished.
