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

# TODO: Create a GKE Autopilot Cluster

# TODO: Create a Firestore Database

# TODO: Create an initial Firestore Document

resource "google_artifact_registry_repository" "my-repo" {
  project     = var.project_id
  location      = "us-central1"
  repository_id = "chat-app-repo"
  description   = "Repository for gradio-based AI chat app"
  format        = "DOCKER"
}

# TODO: Configure Workload Identity IAM bindings

