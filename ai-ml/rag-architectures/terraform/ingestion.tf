# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

### Ingest bucket

resource "google_storage_bucket" "ingest" {
  name = "ingest-${local.unique_str}"

  # Design consideration: Data availability
  location = var.region
}

### Pub/Sub to trigger ingestion job
resource "google_storage_notification" "default" {
  bucket         = google_storage_bucket.ingest.name
  topic          = google_pubsub_topic.ingest.id
  event_types    = ["OBJECT_FINALIZE"]
  payload_format = "JSON_API_V1"

  #depends_on = [google_storage_bucket_iam_member.pubsub]
}

# Allow the Pub/Sub service account the ability to publish messages
resource "google_pubsub_topic_iam_member" "gcs" {
  topic = google_pubsub_topic.ingest.id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${local.gcs_service_account}"

  depends_on = [module.project_services]
}

resource "google_pubsub_topic" "ingest" {
  name = "ingest-${local.unique_str}"

  #depends_on = [ google_storage_bucket_iam_member.pubsub ]
}

# Allow the Pub/Sub service account the ability to publish messages
# TODO(glasnt): confirm if required
#resource "google_project_iam_member" "pubsub" {
#  project = var.project_id
#  role    = "roles/pubsub.publisher"
#  member  = "serviceAccount:${local.pubsub_service_account}"
#  depends_on = [module.project_services]
#}

# Allow the Pub/Sub service account permissions to access the bucket
# TODO(glasnt): confirm if required
#resource "google_storage_bucket_iam_member" "pubsub" {
#  bucket = google_storage_bucket.ingest.name
#  role   = "roles/storage.admin"
#  member = "serviceAccount:${local.pubsub_service_account}"
#
#  depends_on = [module.project_services]
#}

# Function source, taken from function-source

resource "google_storage_bucket" "default" {
  name                        = "gcf-source-${local.unique_str}-${var.project_id}"
  location                    = "US"
  uniform_bucket_level_access = true
}

data "archive_file" "default" {
  type        = "zip"
  output_path = "/tmp/function-source.zip"
  source_dir  = "function-source/"
}

resource "google_storage_bucket_object" "default" {
  name   = "function-source.zip"
  bucket = google_storage_bucket.default.name
  source = data.archive_file.default.output_path
}

# Ingestion function

resource "google_cloudfunctions2_function" "default" {
  name        = "ingestion-${local.unique_str}"
  location    = "us-central1"
  description = "Function to process Cloud Storage events"

  build_config {
    runtime     = "nodejs22"
    entry_point = "processPubSubData"

    source {
      storage_source {
        bucket = google_storage_bucket.default.name
        object = google_storage_bucket_object.default.name
      }
    }
  }

  service_config {
    max_instance_count = 3
    min_instance_count = 1
    available_memory   = "256M"
    timeout_seconds    = 60
    environment_variables = {
      SERVICE_CONFIG_TEST = "config_test"
    }
    ingress_settings               = "ALLOW_INTERNAL_ONLY"
    all_traffic_on_latest_revision = true
    service_account_email          = google_service_account.gcf.email
  }

  event_trigger {
    trigger_region = "us-central1"
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.ingest.id
    retry_policy   = "RETRY_POLICY_RETRY"
  }
}

resource "google_service_account" "gcf" {
  account_id   = "function-service-account"
}
