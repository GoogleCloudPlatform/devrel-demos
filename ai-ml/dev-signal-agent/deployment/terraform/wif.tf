# Workload Identity Federation for GitHub Actions
resource "google_iam_workload_identity_pool" "github_pool" {
  workload_identity_pool_id = "github-actions-pool-devsignal"
  display_name              = "GitHub Actions Pool"
  description               = "Identity pool for GitHub Actions to deploy dev-signal"
}

resource "google_iam_workload_identity_pool_provider" "github_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"
  
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Allow GitHub Actions to act as the agent service account
resource "google_service_account_iam_member" "wif_user" {
  service_account_id = google_service_account.agent_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/attribute.repository/GoogleCloudPlatform/devrel-demos"
}

# Also need token creator for the provider
resource "google_service_account_iam_member" "wif_token_creator" {
  service_account_id = google_service_account.agent_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/attribute.repository/GoogleCloudPlatform/devrel-demos"
}

output "wif_provider_name" {
  value = google_iam_workload_identity_pool_provider.github_provider.name
}

output "wif_service_account" {
  value = google_service_account.agent_sa.email
}
