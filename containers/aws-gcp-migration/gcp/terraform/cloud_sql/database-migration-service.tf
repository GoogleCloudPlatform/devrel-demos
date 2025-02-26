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

resource "google_database_migration_service_connection_profile" "amazon_rds_profile_source" {
  location              = var.cluster_region
  connection_profile_id = "${local.unique_identifier_prefix}-source"
  display_name          = "${local.unique_identifier_prefix} source connection profile"
  project               = google_project_service.datamigration_googleapis_com.project

  postgresql {
    host     = var.source_database_host
    password = var.source_database_password
    port     = var.source_database_port
    username = var.source_database_username
  }
}

resource "google_database_migration_service_connection_profile" "cloud_sql_profile_destination" {
  location              = var.cluster_region
  connection_profile_id = "${local.unique_identifier_prefix}-destination"
  display_name          = "${local.unique_identifier_prefix} destination connection profile"

  cloudsql {
    settings {
      activation_policy         = "ALWAYS"
      auto_storage_increase     = true
      data_disk_type            = "PD_SSD"
      database_version          = "POSTGRES_16"
      edition                   = "ENTERPRISE_PLUS"
      source_id                 = "projects/${google_project_service.datamigration_googleapis_com.project}/locations/us-central1/connectionProfiles/${google_database_migration_service_connection_profile.amazon_rds_profile_source.connection_profile_id}"
      storage_auto_resize_limit = "0"
      tier                      = "db-perf-optimized-N-2"
      zone                      = var.destination_database_zone

      ip_config {
        enable_ipv4 = true
        require_ssl = false
      }
    }
  }
}

resource "google_database_migration_service_migration_job" "demo_migration_job" {
  destination      = google_database_migration_service_connection_profile.cloud_sql_profile_destination.name
  display_name     = "Demo migration job"
  location         = var.cluster_region
  migration_job_id = "demo-migration-job"
  source           = google_database_migration_service_connection_profile.amazon_rds_profile_source.name
  type             = "CONTINUOUS"

  static_ip_connectivity {
  }
}
