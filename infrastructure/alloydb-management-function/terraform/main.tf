# Terraform configuration to deploy the AlloyDB Instance Management Go package
# to two separate Cloud Functions with Pub/Sub triggers via Eventarc.



# --- Provider & API Configuration ---
provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "apis" {
  for_each = toset([
    "cloudfunctions.googleapis.com",
    "eventarc.googleapis.com",
    "pubsub.googleapis.com",
    "alloydb.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "run.googleapis.com",
    "cloudresourcemanager.googleapis.com"
  ])

  project                    = var.project_id
  service                    = each.key
  disable_dependent_services = true
}

# --- Pub/Sub Topics ---
resource "google_pubsub_topic" "manage_instances_trigger" {
  name    = "manage-alloydb-instances-topic"
  project = var.project_id
  depends_on = [
    google_project_service.apis
  ]
}

resource "google_pubsub_topic" "check_instances_trigger" {
  name    = "check-alloydb-instances-topic"
  project = var.project_id
  depends_on = [
    google_project_service.apis
  ]
}

resource "google_pubsub_topic" "instance_alerts" {
  name    = "alloydb-instance-alerts-topic"
  project = var.project_id
  depends_on = [
    google_project_service.apis
  ]
}


# --- Service Account for Cloud Functions ---
resource "google_service_account" "alloydb_functions_sa" {
  account_id   = "alloydb-manager-sa"
  display_name = "Service Account for AlloyDB Management Functions"
  project      = var.project_id
}

# Grant necessary permissions to the Service Account
resource "google_project_iam_member" "sa_alloydb_admin" {
  project = var.project_id
  role    = "roles/alloydb.admin"
  member  = "serviceAccount:${google_service_account.alloydb_functions_sa.email}"
}

# Grant the Service Account permission to publish alerts
resource "google_pubsub_topic_iam_member" "sa_alert_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.instance_alerts.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.alloydb_functions_sa.email}"
}

# --- Source Code Packaging and Upload ---
# Note: Ensure function.go and go.mod are in the same directory.
data "archive_file" "source" {
  type        = "zip"
  source_dir  = "../p"
  output_path = "/tmp/alloydb_functions_source.zip"
}

resource "google_storage_bucket" "bucket" {
  name                        = "${var.project_id}-alloydb-functions"
  location                    = var.region
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "archive" {
  name   = "source.zip#${data.archive_file.source.output_md5}"
  bucket = google_storage_bucket.bucket.name
  source = data.archive_file.source.output_path
}

# --- Cloud Function for Managing Instances ---
resource "google_cloudfunctions2_function" "manage_instances_func" {
  name     = "manage-alloydb-instances"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "go122"
    entry_point = "ManageAlloyDBInstances" # Corresponds to the function name in Go
    source {
      storage_source {
        bucket = google_storage_bucket.bucket.name
        object = google_storage_bucket_object.archive.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    min_instance_count = 0
    timeout_seconds    = 540 # Max timeout for Gen 2
    service_account_email = google_service_account.alloydb_functions_sa.email
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.manage_instances_trigger.id
    retry_policy   = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_project_service.apis
  ]
}

# --- Cloud Function for Checking Instance Parameters ---
resource "google_cloudfunctions2_function" "check_instances_func" {
  name     = "check-alloydb-instances"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "go122"
    entry_point = "CheckAlloyDBInstances" # Corresponds to the function name in Go
    source {
      storage_source {
        bucket = google_storage_bucket.bucket.name
        object = google_storage_bucket_object.archive.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    min_instance_count = 0
    timeout_seconds    = 540 # Max timeout for Gen 2
    service_account_email = google_service_account.alloydb_functions_sa.email
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.check_instances_trigger.id
    retry_policy   = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_project_service.apis
  ]
}
