#Copyright 2023 Google LLC
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.


/*****************************************
Specifies the terraform provider required to run the code
*****************************************/
data "google_project" "project" {
  provider = google-beta
}

/*****************************************
Enables the required API’s within the project - CloudRun + EventArc
*****************************************/
resource "google_project_service" "run-googleapis-com" {
  project = var.gcp_project
  service = "run.googleapis.com"
  disable_dependent_services = true
}
resource "google_project_service" "eventarc" {
  project = var.gcp_project
  provider = google-beta
  service = "eventarc.googleapis.com"
  disable_on_destroy = false
}
/*****************************************
Provides the needed permission to the service account via IAM
*****************************************/
resource "google_project_iam_member" "cps_cr_img" {
  project = var.gcp_project
  role = "roles/iam.serviceAccountTokenCreator"
  member = "serviceAccount:${var.service_account}"
}
resource "google_project_iam_member" "tf-sa-run-adm" {
  project = var.gcp_project
  role = "roles/run.admin"
  member = "serviceAccount:${var.service_account}"
}
resource "google_project_iam_binding" "serviceusage-c" {
  provider = google
  project = var.gcp_project
  role = "roles/serviceusage.serviceUsageConsumer"


  members = [
    "serviceAccount:${var.service_account}"
  ]
}
resource "google_project_iam_binding" "eventrac-r" {
  provider = google
  project = var.gcp_project
  role = "roles/eventarc.serviceAgent"


  members = [
    "serviceAccount:service-${data.google_project.project.number}@gcp-sa-eventarc.iam.gserviceaccount.com","serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com","serviceAccount:${var.service_account}"
  ]
}
resource "google_project_iam_binding" "eventrac-d" {
  provider = google
  project = var.gcp_project
  role = "roles/eventarc.developer"


  members = [
    "serviceAccount:${var.service_account}"
  ]
}


/*****************************************
Creates the CloudRun service that Copies Source container to destination container
Source: Reference
Target: Target Project Location
Image: cloud-run-exec-python:tag
Note: This will require the Image to exist and be uploaded to an AR repo the account has access to.
*****************************************/
resource "google_cloud_run_service" "cloud-run-exec-python" {
  provider = google
  name = "container-image-live"
  depends_on = [
    google_project_service.run-googleapis-com, google_project_iam_member.tf-sa-run-adm, google_project_service.eventarc
  ]
  location = "us-central1"
  template {
    spec {
      service_account_name = "${var.service_account}"
      containers {
        image = "us-docker.pkg.dev/$(SOURCE_PROJECT_ID)/ar/cloud-run-exec-python:tag"
      }
    }
  }
  traffic {
    percent = 100
    latest_revision = true
  }
}

/*****************************************
EventArc Trigger - PubSub -
*****************************************/
resource "google_eventarc_trigger" "trigger_pubsub_tf" {
  provider = google-beta
  project = var.gcp_project
  name = "image-propagation-trigger-2"
  location = google_cloud_run_service.cloud-run-exec-python.location
  depends_on = [google_project_iam_binding.eventrac-d,google_project_iam_binding.eventrac-r,google_cloud_run_service.cloud-run-exec-python]
  matching_criteria {
    attribute = "type"
    value = "google.cloud.pubsub.topic.v1.messagePublished"
  }
  transport {
    pubsub {
#topic = "projects/nubegeeks01/topics/gcr"
      topic = "projects/${var.gcp_project}/topics/${google_pubsub_topic.topic.name}"
    }
  }
  destination {
    cloud_run_service {
      service = google_cloud_run_service.cloud-run-exec-python.name
      region = google_cloud_run_service.cloud-run-exec-python.location
      path = "/image/copy"
    }
  }
  service_account = "${var.service_account}"
}

/*****************************************
This creates the PubSub topic and lets IaC use it as a dependency for other components within the code.
*****************************************/
resource "google_pubsub_topic" "topic" {
  name = "gcr"
}
