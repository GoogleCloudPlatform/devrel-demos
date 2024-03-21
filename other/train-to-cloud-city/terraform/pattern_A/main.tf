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

resource "time_sleep" "wait" {
  create_duration = "45s"
}

locals {
  skaffold    = templatefile("${path.module}/yaml/skaffold.yaml.tftpl", { name = "deployment-pattern-a" })
  default_env = templatefile("${path.module}/yaml/default.yaml.tftpl", { service_name = "hello" })
}

###############
# Enable APIs #
###############

# Enable Cloud Run API
resource "google_project_service" "cloudrun_api" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

# Enable Cloud Deploy API
resource "google_project_service" "clouddeploy_api" {
  service            = "clouddeploy.googleapis.com"
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

# Artifact Registry
resource "google_artifact_registry_repository" "pattern_a_repo" {
  project       = var.project
  location      = var.region
  repository_id = "cloud-train-pattern-a"
  description   = "Cloud Train Demo: Pattern A"
  format        = "DOCKER"
  depends_on = [
    time_sleep.wait
  ]
}

####################
# Service Accounts #
####################
resource "google_service_account" "cloud_build" {
  project    = var.project
  account_id = "cloud-build-main-sa"
}

resource "google_service_account" "cloud_deploy" {
  project    = var.project
  account_id = "cloud-deploy-main-sa"
}

resource "google_project_iam_member" "sa_user" {
  project = var.project
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "logwriter" {
  project = var.project
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "developer" {
  project = var.project
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "storage_admin" {
  project = var.project
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "builds_editor" {
  project = var.project
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "builds_builder" {
  project = var.project
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "job_runner" {
  project = var.project
  role    = "roles/clouddeploy.jobRunner"
  member  = "serviceAccount:${google_service_account.cloud_deploy.email}"
}

##########
# PubSub #
##########

# Create this topic to emit writes to Artifact Registry as events.
# https://cloud.google.com/artifact-registry/docs/configure-notifications#topic
resource "google_pubsub_topic" "gcr" {
  provider = google
  name     = "gcr"
  project  = var.project
}

#######################
# Cloud Build Trigger #
#######################

resource "google_cloudbuild_trigger" "new_build" {
  project         = var.project
  name            = "new-build"
  description     = "Triggers on every change to main branch"
  service_account = google_service_account.cloud_build.id
  included_files = [
    "target/*",
    "target/*/*"
  ]

  github {
    owner = var.repo_owner
    name  = var.repo_name
    push {
      branch = "^main$"
    }
  }

  build {
    options {
      logging = "CLOUD_LOGGING_ONLY"
    }
    step {
      name    = "gcr.io/cloud-builders/gcloud"
      args    = ["builds", "submit", "--tag", "${var.region}-docker.pkg.dev/${var.project}/cloud-train-pattern-a/image", "target/"]
      timeout = "120s"
    }
  }

  depends_on = [
    time_sleep.wait
  ]
}

resource "google_cloudbuild_trigger" "new_release" {
  project         = var.project
  name            = "new-release"
  description     = "Triggers on any new build pushed to Artifact Registry. Creates a new release in Cloud Deploy."
  service_account = google_service_account.cloud_build.id
  pubsub_config {
    topic = google_pubsub_topic.gcr.id
  }
  approval_config {
    approval_required = false
  }

  source_to_build {
    uri       = "https://github.com/${var.repo_owner}/${var.repo_name}"
    ref       = "refs/heads/main"
    repo_type = "GITHUB"
  }

  build {
    options {
      logging = "CLOUD_LOGGING_ONLY"
    }
    step {
      name   = "ubuntu"
      script = "echo ${local.skaffold} > /workspace/skaffold.yaml"
    }
    step {
      name   = "ubuntu"
      script = "echo ${local.default_env} > /workspace/default-env.yaml"
    }
    step {
      name    = "gcr.io/cloud-builders/gcloud"
      args    = ["deploy", "releases", "create", "pattern-A-release", "--project=${var.project}", "--region=${var.region}", "--delivery-pipeline=${google_clouddeploy_delivery_pipeline.default.name}", "--images=${"${var.region}-docker.pkg.dev/${var.project}/cloud-train-pattern-a/image:default"}"]
      timeout = "120s"
    }
  }
}

################
# Cloud Deploy #
################

resource "google_clouddeploy_delivery_pipeline" "default" {
  project     = var.project
  location    = var.region
  name        = "cloud-train-deploy-pipeline"
  description = "Delivery pipeline"
  serial_pipeline {
    stages {
      profiles  = ["default"]
      target_id = google_clouddeploy_target.default_target.name
    }
  }
  depends_on = [
    time_sleep.wait
  ]
}

resource "google_clouddeploy_target" "default_target" {
  provider    = google
  project     = var.project
  location    = var.region
  name        = "cloud-train-default-target"
  description = "Deploy target"

  execution_configs {
    usages          = ["RENDER", "DEPLOY"]
    service_account = google_service_account.cloud_deploy.email
  }
  require_approval = true

  run {
    location = "projects/${var.project}/locations/${var.region}"
  }
}
