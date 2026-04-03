resource "google_model_armor_template" "agent_security_policy" {
  template_id = "agent-security-policy"
  location    = "us-central1"
  project     = var.project

  filter_config {
    # Prompt Injection & Jailbreak
    pi_and_jailbreak_filter_settings {
      filter_enforcement = "ENABLED"
    }

    # Malicious URIs
    malicious_uri_filter_settings {
      filter_enforcement = "ENABLED"
    }

    # RAI Filters
    rai_settings {
      rai_filters {
        filter_type      = "HATE_SPEECH"
        confidence_level = "MEDIUM_AND_ABOVE"
      }
      rai_filters {
        filter_type      = "HARASSMENT"
        confidence_level = "LOW_AND_ABOVE"
      }
    }

    # SDP Linkage (Reference IDs from sdp-template-factory)
    sdp_settings {
      advanced_config {
        inspect_template    = "projects/${var.project}/locations/us-central1/inspectTemplates/agent-pii-inspector"
        deidentify_template = "projects/${var.project}/locations/us-central1/deidentifyTemplates/agent-pii-redactor"
      }
    }
  }

  template_metadata {
    log_template_operations = true
  }
}
