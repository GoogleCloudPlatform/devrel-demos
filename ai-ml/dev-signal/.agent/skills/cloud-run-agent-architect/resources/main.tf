resource "google_project_service" "services" {
  project = var.project_id
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

resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  project       = var.project_id
  repository_id = "${var.service_name}-repo"
  description   = "Docker repository for ${var.service_name}"
  format        = "DOCKER"
  depends_on    = [google_project_service.services]
}

resource "google_service_account" "agent_sa" {
  project      = var.project_id
  account_id   = "${var.service_name}-sa"
  display_name = "${var.service_name} Agent Service Account"
}

resource "google_secret_manager_secret" "agent_secrets" {
  project   = var.project_id
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
  project   = var.project_id
  for_each  = toset(keys(var.secrets))
  secret_id = google_secret_manager_secret.agent_secrets[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_cloud_run_v2_service" "default" {
  project  = var.project_id
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.agent_sa.email
    
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/agent:latest"
     
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = "global"
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "True"
      }
      env {
        name  = "AI_ASSETS_BUCKET"
        value = var.ai_assets_bucket
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
}
