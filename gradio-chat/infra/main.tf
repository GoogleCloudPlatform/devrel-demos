# Configure the Google Cloud Provider
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0" # Use the latest version compatible with your needs
    }
  }
}

variable "project_id" {
  type = string
  description = "Your Google Cloud Project ID"
}

variable "project_number" {
  type = string
  description = "Your Google Cloud Project Number"
}

variable "region" {
  type = string
  description = "The region for your GKE cluster"
  default = "us-central1"
}

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

resource "google_project_service" "container" {
  service            = "container.googleapis.com"
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

variable "cluster_name" {
  type = string
  description = "Name of your GKE cluster"
  default = "gradio-chat-cluster"
}

# Create a GKE Autopilot Cluster
resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region
  project = var.project_id

  # Enable Autopilot mode
  enable_autopilot = true

  deletion_protection = false

  # Networking
  network = "default" # Use the default network or specify a custom one
  subnetwork = "projects/${var.project_id}/regions/${var.region}/subnetworks/default" # Use the default subnetwork or specify a custom one

  # Timeout for cluster creation (adjust as needed)
  timeouts {
    create = "30m" 
    update = "30m"
  }
}

resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = "(default)"
  location_id = "nam5"
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.firestore]
}

resource "google_firestore_document" "initial_document" {
  project     = var.project_id
  collection  = "chat_sessions"
  document_id = "initialize"
  fields = <<EOF
  EOF

  depends_on = [google_firestore_database.database]
}

resource "google_artifact_registry_repository" "my-repo" {
  project     = var.project_id
  location      = "us-central1"
  repository_id = "chat-app-repo"
  description   = "Repository for gradio-based AI chat app"
  format        = "DOCKER"
}