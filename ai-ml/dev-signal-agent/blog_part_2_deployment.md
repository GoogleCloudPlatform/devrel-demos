# Building a "Dev Signal" Agent: Part 2 - Deploying with Terraform

In Part 1, we built the Dev Signal agent with Nano Banana image generation capabilities. Now, we will deploy it to a production-grade environment using **Google Cloud Run** and **Terraform**.

## Why Terraform?

While you can deploy to Google Cloud using the console or `gcloud` CLI, using **Terraform** (Infrastructure as Code) offers critical advantages for production AI systems:

1.  **Reproducibility**: Your entire environment—from IAM roles to Secret Manager versions—is defined in code. You can tear down and rebuild the exact same setup in minutes.
2.  **Security Compliance**: Terraform allows you to audit exactly *who* has access to *what*. In our agent's case, we strictly limit the Service Account's permissions to only what it needs (Vertex AI User, Logging Writer).
3.  **Dependency Management**: Terraform handles the complex order of operations. It knows it must enable the `aiplatform` API *before* it tries to assign a Vertex AI IAM role.
4.  **Drift Detection**: Terraform can detect if someone manually changed a configuration in the console and revert it to the declared state, ensuring your production environment remains stable.

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

We will build our infrastructure in logical blocks.

### 1. Enable APIs
First, we enable the necessary Google Cloud services. This ensures that even in a fresh project, all required APIs (like Vertex AI and Secret Manager) are active.

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
```

### 2. Artifact Registry
We create a Docker repository to store our agent's container images. This gives us a private, secure place to push our builds.

```hcl
# 2. Artifact Registry Repository
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "dev-signal-repo"
  description   = "Docker repository for Dev Signal Agent"
  format        = "DOCKER"
  depends_on    = [google_project_service.services]
}
```

### 3. Identity (Service Account & IAM)
**Security Best Practice**: We create a dedicated Service Account for the agent. Instead of giving it broad "Editor" permissions, we grant it *only* the specific roles it needs:
*   `roles/aiplatform.user`: To call Vertex AI models.
*   `roles/logging.logWriter`: To send telemetry and logs to Cloud Logging.

```hcl
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
```

### 4. Secret Management
We use Google Secret Manager to securely store API keys (like `DK_API_KEY` and Reddit credentials). This Terraform code iterates over your `secrets` variable, creates the secrets, and grants the agent's Service Account permission (`roles/secretmanager.secretAccessor`) to read them.

```hcl
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
```

### 5. Cloud Run Service
Finally, we deploy the container. Notice how we inject the secrets as environment variables dynamically. We also override `GOOGLE_CLOUD_LOCATION` to `global` to ensure compatibility with Vertex AI Preview models.

```hcl
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

By default, our Cloud Run service is private. To access it, you need to use the **Cloud Run Proxy** and ensure your user has the correct permissions.

### 1. Granting User Permissions
Before you can invoke the service, you must grant your Google account the `roles/run.invoker` role for this specific service. Run the following command:

```bash
gcloud run services add-iam-policy-binding dev-signal-agent \
  --member="user:your-email@example.com" \
  --role="roles/run.invoker" \
  --region=us-central1 \
  --project=your-project-id
```

### 2. Launch the Proxy
Now, access your private service securely via the proxy:

```bash
gcloud run services proxy dev-signal-agent \
  --region us-central1 \
  --project your-project-id
```

Visit **`http://localhost:8080`** to chat with your deployed agent!