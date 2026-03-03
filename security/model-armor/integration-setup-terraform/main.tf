# Setup Terraform and Google provider for Terraform

terraform {
  required_version = ">= 1.14.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.20"
    }
  }
}

provider "google" {
  project = var.project_id
}

# Enable services (assuming that Vertex AI and relevant MCP services are enabled)

locals {
  google_apis = [
    "modelarmor.googleapis.com",
    "dlp.googleapis.com"
  ]
  integrated_services = concat(
    [],
    var.vertex_ai_integration ? ["AI_PLATFORM"] : [],
    var.mcp_integration ? ["GOOGLE_MCP_SERVER"] : []
  )
}

resource "google_project_service" "google_apis" {
  for_each = toset(local.google_apis)
  project  = var.project_id
  service  = each.value
}

# Enable integration with Vertex AI and Google Cloud MCP servers

resource "google_model_armor_floorsetting" "floorsetting-filter-config" {
  location    = "global"
  parent      = "projects/${var.project_id}"
  filter_config {
    rai_settings {
      rai_filters {
        filter_type      = "DANGEROUS"
        confidence_level = "MEDIUM_AND_ABOVE"
      }
    }
    sdp_settings {
      basic_config {
        filter_enforcement = "ENABLED"
      }
    }
    pi_and_jailbreak_filter_settings {
      filter_enforcement = "ENABLED"
      confidence_level   = "HIGH"
    }
    malicious_uri_filter_settings {
      filter_enforcement = "ENABLED"
    }
  }
  integrated_services = local.integrated_services
  ai_platform_floor_setting {
    inspect_and_block = true
  }
}