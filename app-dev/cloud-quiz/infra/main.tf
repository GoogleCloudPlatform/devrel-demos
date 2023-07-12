/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

### Secret Manager resources ###

resource "random_id" "nextauth_secret" {
  byte_length = 32
}

resource "google_secret_manager_secret" "nextauth_secret" {
  project   = var.project_id
  secret_id = "${var.deployment_name}-nextauth-secret"
  replication {
    automatic = true
  }
  labels = var.labels
  depends_on = [
    time_sleep.project_services
  ]
}

resource "google_secret_manager_secret_version" "nextauth_secret" {
  secret      = google_secret_manager_secret.nextauth_secret.id
  secret_data = random_id.nextauth_secret.b64_std
  depends_on = [
    google_secret_manager_secret.nextauth_secret
  ]
}

# Assumption: That this is a blank project, and nobody created a Firestore database
# previously.
resource "google_firestore_database" "database" {
  project                     = var.project_id
  name                        = "(default)"
  location_id                 = "nam5"
  type                        = "FIRESTORE_NATIVE"
  concurrency_mode            = "PESSIMISTIC"
  app_engine_integration_mode = "DISABLED"
  depends_on = [
    time_sleep.project_services
  ]
}
