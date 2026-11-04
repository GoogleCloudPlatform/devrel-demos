# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" { 
  type = string 
}

variable "region" { 
  type    = string
  default = "us-central1" 
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# TODO(production): For production, connect over Private Service Connect instead of a public endpoint.
# Ensure the following enterprise network components are configured:
# 1. Serverless VPC Access Connector for Cloud Run outbound traffic.
# 2. Private Service Connect (PSC) endpoints for Cloud SQL / AlloyDB.
# 3. Cloud Armor WAF policies attached to internal Application Load Balancer.
# 4. VPC Service Controls (VPC-SC) perimeter configuration around Vertex AI APIs.

locals {
  # Placeholder for authorized network parameters
  vpc_connector_id = "projects/${var.project_id}/locations/${var.region}/connectors/sec-agent-connector"
}

# --- Private Services Access Networking ---
resource "google_project_service" "servicenetworking" {
  service = "servicenetworking.googleapis.com"
}

resource "google_compute_global_address" "private_ip_range" {
  name          = "kb-private-ip-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = "projects/${var.project_id}/global/networks/default"
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = "projects/${var.project_id}/global/networks/default"
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
  depends_on              = [google_project_service.servicenetworking]
}

# Cloud SQL PostgreSQL Instance with pgvector support
resource "google_sql_database_instance" "knowledge_store" {
  name             = "kb-lowlatency-store"
  database_version = "POSTGRES_15"
  region           = var.region

  # TODO(production): Turn deletion_protection back to true in production
  deletion_protection = false
  depends_on          = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-custom-4-16384"

    # Database flags to activate vector performance extensions
    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }

    ip_configuration {
      # In production, require private IP exclusively
      ipv4_enabled    = false
      private_network = "projects/${var.project_id}/global/networks/default"
      
      # TODO(production): Verify PSC vs VPC Peering allocation
    }
  }
}

# Pub/Sub Topic for Subtask 5 Asynchronous Telemetry
resource "google_pubsub_topic" "agent_telemetry" {
  name = "agent-session-telemetry"
}
