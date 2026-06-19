provider "google" {
  project = var.project_id
}
data "google_project" "project" {}

# 1. Define the Pub/Sub Topic for Alert Notifications
resource "google_pubsub_topic" "alert_topic" {
  name = "api-key-alert-notifications"
}

# 2. Define the Cloud Monitoring Notification Channel targeting the Pub/Sub topic
resource "google_monitoring_notification_channel" "pubsub_channel" {
  display_name = "Pub/Sub Alert Channel"
  type         = "pubsub"
  labels = {
    topic = google_pubsub_topic.alert_topic.id
  }
}

# 3. Define the Cloud Monitoring Alert Policy using PromQL
resource "google_monitoring_alert_policy" "api_spike_alert" {
  display_name = "Credential API Request Count Increase Alert (PromQL)"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "API Request Count Increase > 10% in 5m with Min Volume"

    condition_prometheus_query_language {
      # We inject the var.api_key_uid variable directly into the PromQL query
      query = "(sum(increase(serviceruntime_googleapis_com:api_request_count{metric_label_credential_id=\"${var.api_key_uid}\"}[5m])) / sum(increase(serviceruntime_googleapis_com:api_request_count{metric_label_credential_id=\"${var.api_key_uid}\"}[5m] offset 5m)) > 1.10) and (sum(increase(serviceruntime_googleapis_com:api_request_count{metric_label_credential_id=\"${var.api_key_uid}\"}[5m])) > 50)"
      
      duration            = "0s"
      evaluation_interval = "60s"
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.pubsub_channel.name
  ]
}

# 4. IAM Permissions: Allow Cloud Build Service Account to delete API Keys
# Note: Cloud Build uses its default or a specified service account. 
# Here we grant the standard Cloud Build SA the 'apikeys.admin' role.
resource "google_project_iam_member" "cloudbuild_api_key_admin" {
  project = var.project_id
  role    = "roles/apikeys.admin"
  member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

# 5. Define the Cloud Build Trigger that reacts to the Pub/Sub Topic
resource "google_cloudbuild_trigger" "delete_key_trigger" {
  name        = "delete-compromised-api-key"
  description = "Triggered by Pub/Sub alert to automatically delete the leaking API Key"

  # Bind the trigger to listen to the Pub/Sub topic
  pubsub_config {
    topic = google_pubsub_topic.alert_topic.id
  }

  # Build configuration that runs inline to delete the key via gcloud
  build {
    step {
      name = "gcr.io/google.com/cloudsdktool/cloud-sdk:slim"
      args = [
        "gcloud", "services", "api-keys", "delete", var.api_key_uid, "--quiet"
      ]
    }
  }

  depends_on = [google_project_iam_member_cloudbuild_api_key_admin]
}