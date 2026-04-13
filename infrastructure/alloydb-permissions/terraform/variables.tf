variable "project_id" {
  description = "The ID of the Google Cloud project."
  type        = string
}

variable "region" {
  description = "The region to deploy resources in."
  type        = string
  default     = "us-central1"
}

variable "cluster_id" {
  description = "The ID of the AlloyDB cluster."
  type        = string
  default     = "rma-cluster"
}

variable "instance_id" {
  description = "The ID of the AlloyDB instance."
  type        = string
  default     = "rma-instance-1"
}

variable "service_account_name" {
  description = "The name of the service account."
  type        = string
  default     = "auth-demo-sa"
}

variable "cloud_run_service_name" {
  description = "The name of the Cloud Run service."
  type        = string
  default     = "auth-issue-demo"
}

variable "cloud_run_image" {
  description = "The container image for the Cloud Run service."
  type        = string
}

variable "db_password" {
  description = "The database password. If not provided, a random one will be generated."
  type        = string
  sensitive   = true
  default     = null
}
