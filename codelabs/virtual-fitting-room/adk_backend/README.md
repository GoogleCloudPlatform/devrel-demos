# Go ADK backend for Virtual Try On

Prereqs:
- An API key
    - needs at least API access for Cloud Storage, and Gemini
- A cloud storage bucket
    - used for artifact storage.

## Setup

- create a `.env` file, filling the fields from `example.env`

- Run `source .env`

- Upload the product images to your storage bucket.
    - `gcloud storage cp -r ../assets/* gs://$GCS_BUCKET/catalog-assets`

- Run `gcloud auth application-default login`

- run `go run . web api webui` to start the API server and the dev webui.
