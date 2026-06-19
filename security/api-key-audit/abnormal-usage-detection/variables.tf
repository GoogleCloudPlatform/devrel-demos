variable "project_id" {
  type        = string
  description = "The GCP Project ID where resources will be managed."
}

variable "api_key_uid" {
  type        = string
  description = "The unique ID of the API key to monitor and potentially delete."
}