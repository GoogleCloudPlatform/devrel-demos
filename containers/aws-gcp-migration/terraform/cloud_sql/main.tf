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

resource "google_sql_database_instance" "demo_cloudsql_instance" {
  name = "${local.unique_identifier_prefix}-instance"

  database_version    = "POSTGRES_16"
  deletion_protection = false
  project             = google_project_service.sqladmin_googleapis_com.project
  region              = var.cluster_region

  settings {
    disk_type = "PD_SSD"
    edition   = "ENTERPRISE_PLUS"
    tier      = "db-perf-optimized-N-2"
  }
}

resource "google_sql_database" "accounts" {
  name     = "accounts-db"
  instance = google_sql_database_instance.demo_cloudsql_instance.name
  project  = google_project_service.sqladmin_googleapis_com.project
}

resource "google_sql_database" "ledger" {
  name     = "ledger-db"
  instance = google_sql_database_instance.demo_cloudsql_instance.name
  project  = google_project_service.sqladmin_googleapis_com.project
}
