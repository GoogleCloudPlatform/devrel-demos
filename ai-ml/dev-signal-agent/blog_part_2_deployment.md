# Building a "Dev Signal" Agent: Part 2 - Deploying with Terraform

In Part 1, we built the Dev Signal agent with Nano Banana image generation capabilities. Now, we will deploy it to a production-grade environment using **Google Cloud Run** and **Terraform**.

## Prerequisites

*   Google Cloud SDK (`gcloud`) installed and authenticated.
*   Terraform installed.
*   A Google Cloud Project.

## Step 1: Define Infrastructure

Create a `deployment/terraform` directory. We will add files to define our Google Cloud environment.

**File:** `deployment/terraform/variables.tf`
```hcl
variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The Google Cloud region to deploy to"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
  default     = "dev-signal-agent"
}

variable "secrets" {
  description = "A map of secret names and their values (e.g., REDDIT_CLIENT_ID, DK_API_KEY)"
  type        = map(string)
  default     = {}
}
```

**File:** `deployment/terraform/main.tf`
This configuration deploys Cloud Run, sets up IAM roles for Vertex AI and Logging, and securely handles secrets.

```hcl
# 1. Enable Google Cloud APIs
resource "google_project_service" "services" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "aiplatform.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com"
  ])
  service            = each.key
  disable_on_destroy = false
}

# 2. Artifact Registry Repository
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "dev-signal-repo"
  description   = "Docker repository for Dev Signal Agent"
  format        = "DOCKER"
  depends_on    = [google_project_service.services]
}

# 3. Service Account for the Agent
resource "google_service_account" "agent_sa" {
  account_id   = "${var.service_name}-sa"
  display_name = "Dev Signal Agent Service Account"
}

# 4. IAM Roles for the Agent
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

# 5. Secret Manager for Sensitive Keys
resource "google_secret_manager_secret" "agent_secrets" {
  for_each  = toset(keys(var.secrets))
  secret_id = each.key
  
  replication {
    auto {}
  }
  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_version" "agent_secrets_version" {
  for_each    = toset(keys(var.secrets))
  secret      = google_secret_manager_secret.agent_secrets[each.key].id
  secret_data = var.secrets[each.key]
}

resource "google_secret_manager_secret_iam_member" "secret_accessor" {
  for_each  = toset(keys(var.secrets))
  secret_id = google_secret_manager_secret.agent_secrets[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_sa.email}"
}

# 6. Cloud Run Service
resource "google_cloud_run_v2_service" "default" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.agent_sa.email
    
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      # IMPORTANT: Vertex AI Preview models are often global-only.
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = "global"
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "True"
      }

      # Inject Secrets as Environment Variables
      dynamic "env" {
        for_each = var.secrets
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.agent_secrets[env.key].secret_id
              version = "latest"
            }
          }
        }
      }
      
      resources {
        limits = {
          cpu    = "1"
          memory = "2Gi"
        }
      }
    }
  }
  
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.services]
}
```

## Step 2: Configure Secrets and Provision

Create `deployment/terraform/terraform.tfvars` with your actual project details:

```hcl
project_id = "your-project-id"

secrets = {
  REDDIT_CLIENT_ID     = "your_reddit_client_id"
  REDDIT_CLIENT_SECRET = "your_reddit_client_secret"
  DK_API_KEY           = "your_dk_api_key"
}
```

Deploy the infrastructure:
```bash
cd deployment/terraform
terraform init
terraform apply
```

## Step 3: Build and Deploy Code

We use **Cloud Build** to build our container. Since our agent includes the local Nano Banana tool code, it will be packaged into the container automatically.

Run this command from your project root:
```bash
make docker-deploy
```

This make command performs two key steps:
1.  Submits a build to Google Cloud Build, tagging the image in the Artifact Registry.
2.  Updates the Cloud Run service to use the newly built image.

## Step 4: Secure Access

Access your private service securely via the **Cloud Run Proxy**:

```bash
gcloud run services proxy dev-signal-agent \
  --region us-central1 \
  --project your-project-id
```

Visit **`http://localhost:8080`** to chat with your deployed agent!