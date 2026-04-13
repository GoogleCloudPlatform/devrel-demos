# AlloyDB Auth Demo

This project demonstrates an authentication issue when connecting to AlloyDB from Cloud Run, specifically in a cross-project scenario.

## Directory Structure

- `setup_via_tf.sh`: Script to initialize Terraform, apply changes, and deploy the application.
- `terraform/`: Contains Terraform configuration for infrastructure.
- `auth_issue_demo/`: Contains the application code.
    - `main.py`: Flask application that connects to AlloyDB.
    - `Dockerfile`: Dockerfile for the application.
    - `requirements.txt`: Python dependencies.
    - `test_app.py`: Unit tests for the application.

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and configured.
- Terraform installed.
- Access to a Google Cloud project with AlloyDB enabled.
- A `.env` file in the root directory with `PROJECT_ID=your-project-id`.

## Deployment

### 1. Infrastructure Setup (Terraform)

We use Terraform to manage the infrastructure. To initialize, apply changes, and deploy the app, run:

```bash
./setup_via_tf.sh
```

To apply the changes and let Terraform manage the resources:

```bash
cd terraform
terraform apply -var="project_id=$PROJECT_ID" -var="cloud_run_image=<image_uri>"
```

### 2. Updating the Application

If you make changes to the application code in `auth_issue_demo/`, you can deploy updates using `gcloud run deploy` with source upload:

```bash
gcloud run deploy auth-issue-demo \
    --source auth_issue_demo \
    --region us-central1 \
    --project $PROJECT_ID
```

## Testing for Auth Error

After deployment, you will get a target URL.

### 1. Verify Failure (Auth Issue)

Access the `/connect` endpoint of the deployed service.

```bash
curl <SERVICE_URL>/connect
```

**Expected Result:** A `500` error with details indicating a permission denial or connection failure.

### 2. Resolve the Issue

Grant the necessary role to the service account.

```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
    --member="serviceAccount:auth-demo-sa@<PROJECT_ID>.iam.gserviceaccount.com" \
    --role="roles/alloydb.client"
```

### 3. Verify Success

After granting the permission, test the endpoint again.

```bash
curl <SERVICE_URL>/connect
```

**Expected Result:** `SUCCESS: Connected to AlloyDB! DB Time: ...`
