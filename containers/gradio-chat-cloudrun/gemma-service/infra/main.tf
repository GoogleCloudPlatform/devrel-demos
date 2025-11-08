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

variable "region" {
  type        = string
  description = "The region for your Cloud Run service"
  default     = "us-central1"
}

# Enable necessary APIs
resource "google_project_service" "run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
  project            = var.project_id
}

# Cloud Run Service for Gemma
resource "google_cloud_run_v2_service" "gemma_service" {
  name     = "gemma-service"
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    timeout = "600s"
    max_instance_request_concurrency = 4
    gpu_zonal_redundancy_disabled = "true"

    containers {
      # Using Google's prebuilt Gemma container (Ollama-based)
      image = "us-docker.pkg.dev/cloudrun/container/gemma/gemma3-4b"

      resources {
        limits = {
          cpu              = "8"
          memory           = "32Gi"
          "nvidia.com/gpu" = "1"
        }
        startup_cpu_boost = true
      }

      env {
        name  = "OLLAMA_NUM_PARALLEL"
        value = "4"
      }
      
      # Ensure it uses the right port for Cloud Run (Ollama container likely listens on 8080 by default or via PORT env)
      ports {
        container_port = 8080
      }
      
      startup_probe {
        initial_delay_seconds = 60
        timeout_seconds = 240
        period_seconds = 10
        failure_threshold = 30
        tcp_socket {
          port = 8080
        }
      }
    }

    node_selector {
      accelerator = "nvidia-l4"
    }

    scaling {
      max_instance_count = 1
      min_instance_count = 0 # Scale to zero to save money when not in use
    }
  }

  depends_on = [
    google_project_service.run
  ]
}

output "gemma_service_url" {
  description = "The URL of the deployed Gemma service"
  value       = google_cloud_run_v2_service.gemma_service.uri
}