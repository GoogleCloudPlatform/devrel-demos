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
      # We override this to "global" so the SDK hits the correct endpoint,
      # even if the Cloud Run service itself is in us-central1.
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

