variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region to deploy to"
  type        = string
  default     = "us-central1"
}

variable "backend_image" {
  description = "The Docker image for the backend"
  type        = string
}

variable "frontend_image" {
  description = "The Docker image for the frontend"
  type        = string
}

variable "revision_id" {
  description = "A unique ID to force a new revision"
  type        = string
  default     = "none"
}
