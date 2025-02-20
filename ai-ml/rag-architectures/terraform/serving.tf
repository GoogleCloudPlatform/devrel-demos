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


### Frontend service

resource "google_cloud_run_v2_service" "serving" {
  name     = "serving-${local.unique_str}"
  location = var.region

  template {
    containers {
      # Note: Replace with the customized container image.
      image = "us-docker.pkg.dev/cloudrun/container/hello"
    }
  }

  deletion_protection = false
  depends_on          = [module.project_services]
}

# Design consideration: Allow front-end to be publicly accessible.
resource "google_cloud_run_v2_service_iam_member" "public" {
  location = google_cloud_run_v2_service.serving.location
  name     = google_cloud_run_v2_service.serving.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}


### Backend service

resource "google_cloud_run_v2_service" "backend" {
  name     = "backend-${local.unique_str}"
  location = var.region

  # Design Consideration: Ingress security
  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    containers {
      # Note: Replace with the customized container image.
      image = "us-docker.pkg.dev/cloudrun/container/hello"
    }
  }

  deletion_protection = false
  depends_on          = [module.project_services]
}
