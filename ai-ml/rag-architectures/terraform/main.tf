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

# Used to get Google Cloud project number
data "google_project" "default" {}

# Cloud Pub/Sub service account email identifier
locals { pubsub_service_account = "service-${data.google_project.default.number}@gcp-sa-pubsub.iam.gserviceaccount.com" }

# Cloud Storage service account email identifier
data "google_storage_project_service_account" "gcs_account" {}
locals { gcs_service_account = data.google_storage_project_service_account.gcs_account.email_address }


## Enable APIs

module "project_services" {
  source                      = "terraform-google-modules/project-factory/google//modules/project_services"
  version                     = "~> 18.0"
  disable_services_on_destroy = false
  project_id                  = var.project_id

  activate_apis = [
    "run.googleapis.com",
    "pubsub.googleapis.com",
    "aiplatform.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
  ]
}
