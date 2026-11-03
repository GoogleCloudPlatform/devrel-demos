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

# =========================================================================
# NETWORKING PLACEHOLDER (Review with Deepak Michael)
# =========================================================================
# TODO: Finalize the following enterprise network components with Deepak Michael:
# 1. Serverless VPC Access Connector for Cloud Run outbound traffic.
# 2. Private Service Connect (PSC) endpoints for Cloud SQL / AlloyDB.
# 3. Cloud Armor WAF policies attached to internal Application Load Balancer.
# 4. VPC Service Controls (VPC-SC) perimeter configuration around Vertex AI APIs.

locals {
  # Placeholder for authorized network parameters
  vpc_connector_id = "projects/${var.project_id}/locations/${var.region}/connectors/sec-agent-connector"
}

# Cloud SQL PostgreSQL Instance with pgvector support
resource "google_sql_database_instance" "knowledge_store" {
  name             = "kb-lowlatency-store"
  database_version = "POSTGRES_15"
  region           = var.region

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
      
      # NETWORKING PLACEHOLDER: Deepak Michael to verify PSC vs VPC Peering allocation
    }
  }
}

# Pub/Sub Topic for Subtask 5 Asynchronous Telemetry
resource "google_pubsub_topic" "agent_telemetry" {
  name = "agent-session-telemetry"
}
