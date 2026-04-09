# Code to Cloud Demo

This project demonstrates a multi-region, two-tier web application deployed on Google Cloud Run with cross-region data transfer via Google Cloud Storage (GCS). It is designed to showcase service-to-service communication, IAM security, and multi-region architecture.

> [!WARNING]
> **Cost Disclaimer**: Running this demo at full capacity (1000 pings per minute) can cost approximately $50 per day due to GCS operations and cross-region data transfer. The default configuration in Cloud Scheduler has been reduced to ensure costs remain under $3 per day. Always monitor your billing and delete resources when they are no longer needed.

## Architecture

The application consists of the following components:

*   **Frontend**: A Cloud Run service that serves a web interface and proxies requests to the backend.
*   **Backend Services**: Three instances of the backend service running in different regions:
    *   `us-central1`
    *   `us-east4`
    *   `europe-west1`
*   **Storage**: Three regional GCS buckets, one for each region.
*   **Ring Configuration**: The backend services are configured to write data to their local bucket and copy it to the destination bucket in the next region, forming a static ring. Note that this is a one-step copy triggered per request, not automatic full-ring replication:
    *   `us-central1` -> `us-east4`
    *   `us-east4` -> `europe-west1`
    *   `europe-west1` -> `us-central1`
*   **Cloud Scheduler**: A job that pings the frontend regularly to simulate traffic.

## GCS Transfer Implementation

When the application is invoked with `mode=gcs`, the backend executes the following steps to perform the cross-region copy:

1. **Data Retrieval**: The backend reads the request body to determine the data payload to be stored.
2. **Source Write**: It generates a unique object name (format: `ping-<timestamp>-<hostname>`) and writes the payload to the regional bucket specified by the `BUCKET_NAME` environment variable.
3. **Cross-Region Copy**: Once the file is written, the backend uses the Cloud Storage client's `CopierFrom` method to copy the object directly to the destination bucket specified by the `DEST_BUCKET_NAME` environment variable.
4. **Ring Configuration**: This defines a static ring path across regions because Terraform configures each regional backend service with:
    * `BUCKET_NAME` set to the bucket in its own region.
    * `DEST_BUCKET_NAME` set to the bucket in the *next* region in the ring.

## Prerequisites

*   **Google Cloud SDK (`gcloud`)**: Installed and authenticated.
*   **Terraform**: Installed on your system.
*   **Project**: A Google Cloud project with billing enabled.

> [!NOTE]
> Docker is **not** required to be installed locally. The deployment script uses Google Cloud Build to build container images in the cloud.

## Deployment

Deployment is automated using scripts and Terraform.

### Step 1: Project Setup

Run the setup script to enable the necessary APIs and grant required IAM roles to your user account.

```bash
./scripts/setup.sh <PROJECT_ID>
```

If you don't provide a `PROJECT_ID`, it will try to use the current project configured in `gcloud`.

### Step 2: Deploy Infrastructure

Run the deployment script to build the container images and deploy the infrastructure via Terraform.

```bash
./scripts/deploy.sh <PROJECT_ID>
```

This script will:
1.  Build the backend and frontend images using Cloud Build.
2.  Initialize and apply Terraform configuration.
3.  Output the URL of the deployed frontend.

## Using the Examples

Once deployed, you can interact with the application using the frontend URL.

### Endpoints

*   **Standard Ping**:
    Pings the backend to confirm connectivity.
    ```bash
    curl <FRONTEND_URL>/api/ping?mode=standard
    ```

*   **GCS Transfer Mode**:
    Triggers a file write to the local bucket and a copy to the next bucket in the ring.
    ```bash
    curl <FRONTEND_URL>/api/ping?mode=gcs
    ```

*   **Payload Size Testing**:
    Sends a payload of a specific size (in bytes) to the backend.
    ```bash
    curl -X POST <FRONTEND_URL>/api/ping?size=1024
    ```

*   **Batch Ping**:
    Performs a batch of pings to the backend.
    ```bash
    curl <FRONTEND_URL>/api/batch-ping?count=10&mode=standard
    ```

## Automated Testing

You can run the end-to-end test script to verify that all components are working correctly.

```bash
./scripts/e2e_test.sh <FRONTEND_URL>
```
