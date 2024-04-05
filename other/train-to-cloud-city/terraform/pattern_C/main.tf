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

####################
# Service Accounts #
####################

resource "google_cloud_run_service_iam_member" "member" {
    service = google_cloud_run_service.run.name
    location = google_cloud_run_service.run.location
    role = "roles/run.invoker"
    member = "allUsers"
}

####################
#     Cloud SQL    #
####################

resource "google_sql_database_instance" "instance" {
    name = "cloud_train_pattern_c_sql_db"
    region = var.region
    database_version="POSTGRES_13"
    deletion_protection = false
    settings{
        tier="db-f1-micro"
    }
}

resource "google_sql_database" "database"{
    name="cloud_train_sql_db"
    instance=google_sql_database_instance.instance.name
}

resource "google_sql_user" "database-user" {
    name = var.database_user
    instance = google_sql_database_instance.instance.name
    password = var.database_password
}

####################
#     Cloud Run    #
####################

resource "google_cloud_run_v2_service" "pattern_c_run" {
    name="pattern_c_service"
    location = "us-central1"
    template {
        spec {
            containers {
                image = "us-docker.pkg.dev/cloudrun/container/hello"
                ports {
                    container_port = 5000
                }
                env {
                    name="ENV"
                    value = "production"
                }
                env {
                    name="JWT_KEY"
                    value = var.jwt_key
                }
                env {
                    name="DB_URL"
                    value = "postgresql://${var.database_user}:${var.database_password}@/cloud_train_sql_db?host=/cloudsql/${google_sql_database_instance.instance.connection_name}"
                }
            }
        }
        metadata {
            annotations = {
                "run.googleapis.com/cloudsql-instances"=google_sql_database_instance.instance.connection_name
            }
        }
    }
}
