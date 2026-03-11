resource "google_data_loss_prevention_inspect_template" "agent_pii_inspector" {
  parent       = "projects/${var.project}/locations/us-central1"
  display_name = "Agent PII Inspector"
  template_id  = "agent-pii-inspector"

  inspect_config {
    info_types { name = "PERSON_NAME" }
    info_types { name = "EMAIL_ADDRESS" }
    info_types { name = "CREDIT_CARD_NUMBER" }
    info_types { name = "GCP_API_KEY" }
    info_types { name = "STREET_ADDRESS" }
  }
}

resource "google_data_loss_prevention_deidentify_template" "agent_pii_redactor" {
  parent       = "projects/${var.project}/locations/us-central1"
  display_name = "Agent PII Redactor"
  template_id  = "agent-pii-redactor"

  deidentify_config {
    info_type_transformations {
      transformations {
        primitive_transformation {
          replace_config {
            new_value { string_value = "[redacted]" }
          }
        }
      }
    }
  }
}
