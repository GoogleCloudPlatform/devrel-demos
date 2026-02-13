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

variable "ai_assets_bucket" {
  description = "The GCS bucket for storing AI assets"
  type        = string
}
