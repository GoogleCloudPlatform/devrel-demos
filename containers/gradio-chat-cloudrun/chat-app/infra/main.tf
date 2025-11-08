# Configure the Google Cloud Provider
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

variable "project_id" {
  type        = string
  description = "Your Google Cloud Project ID"
}

variable "project_number" {
  type        = string
  description = "Your Google Cloud Project Number"
}

variable "region" {
  type        = string
  description = "The region for your Cloud Run service"
  default     = "us-central1"
}

# Enable necessary APIs
resource "google_project_service" "cloudbuild" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
  project            = var.project_id
}

resource "google_project_service" "artifactregistry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
  project            = var.project_id
}

resource "google_project_service" "run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
  project            = var.project_id
}

resource "google_project_service" "firestore" {
  service            = "firestore.googleapis.com"
  disable_on_destroy = false
  project            = var.project_id
}

resource "google_project_service" "vertexai" {
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
  project            = var.project_id
}

# Artifact Registry Repository for container images
resource "google_artifact_registry_repository" "chat_app_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "chat-app-repo"
  description   = "Repository for Cloud Run chat app images"
  format        = "DOCKER"
  depends_on    = [google_project_service.artifactregistry]
}

# Firestore Database
resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = "chat-app-db"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.firestore]
}

# Service Account for Cloud Run
resource "google_service_account" "run_sa" {
  project      = var.project_id
  account_id   = "chat-app-run-sa"
  display_name = "Service Account for Cloud Run Chat App"
}

# IAM bindings for the Service Account
resource "google_project_iam_member" "run_sa_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.run_sa.email}"
}

resource "google_project_iam_member" "run_sa_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.run_sa.email}"
}

# Grant the service account permission to invoke other Cloud Run services (like Gemma)
resource "google_project_iam_member" "run_sa_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.run_sa.email}"
}