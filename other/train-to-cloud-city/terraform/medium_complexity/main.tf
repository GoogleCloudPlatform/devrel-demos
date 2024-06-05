# Copyright 2024 Google LLC
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

provider "google" {
  project = var.project
  region  = var.region
}

locals {
  plant_data = jsondecode(file("${path.module}/data/plants.json"))
}

data "template_file" "plants_json" {
  template = file("${path.module}/data/plant.tftpl")
  count    = length(local.plant_data)
  vars = {
    id   = count.index
    name = local.plant_data[count.index].data.name
    type = local.plant_data[count.index].data.type
  }
}

resource "time_sleep" "wait" {
  create_duration = "60s"
}

###############
# Enable APIs #
###############

# Enable Cloud Run API
resource "google_project_service" "cloudrun_api" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

# Enable Cloud Build API
resource "google_project_service" "cloudbuild_api" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

# Enable Artifact Registry API
resource "google_project_service" "artifactregistry_api" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# Enable Cloud Firestore API
resource "google_project_service" "firestore" {
  project    = var.project
  service    = "firestore.googleapis.com"
  depends_on = [time_sleep.wait]
}

#####################
# Artifact Registry #
#####################

resource "google_artifact_registry_repository" "ar_repo" {
  project       = var.project
  location      = var.region
  repository_id = "cloud-train"
  description   = "Cloud Train Demo Repo"
  format        = "DOCKER"
}

#####################
#  Cloud Firestore  #
#####################

resource "google_firestore_database" "database" {
  project     = var.project
  name        = "(default)"
  location_id = "nam5"
  type        = "FIRESTORE_NATIVE"
  depends_on = [google_project_service.firestore]
}

resource "google_firestore_document" "plants_doc_1" {
  project     = var.project
  collection  = "plants"
  database    = google_firestore_database.database.name
  document_id = "plants_doc_1"
  fields      = data.template_file.plants_json[0].rendered
}

resource "google_firestore_document" "plants_doc_2" {
  project     = var.project
  collection  = "plants"
  database    = google_firestore_database.database.name
  document_id = "plants_doc_2"
  fields      = data.template_file.plants_json[1].rendered
}

resource "google_firestore_document" "plants_doc_3" {
  project     = var.project
  collection  = "plants"
  database    = google_firestore_database.database.name
  document_id = "plants_doc_3"
  fields      = data.template_file.plants_json[2].rendered
}

