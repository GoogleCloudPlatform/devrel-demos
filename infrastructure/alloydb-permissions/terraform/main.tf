provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable APIs
locals {
  apis = [
    "alloydb.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "compute.googleapis.com",
    "geminicloudassist.googleapis.com",
    "monitoring.googleapis.com",
    "cloudasset.googleapis.com",
    "cloudbuild.googleapis.com",
    "recommender.googleapis.com",
    "appoptimize.googleapis.com",
    "secretmanager.googleapis.com"
  ]
}

resource "random_password" "db_pass" {
  count            = var.db_password == null ? 1 : 0
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

locals {
  db_password = var.db_password != null ? var.db_password : random_password.db_pass[0].result
}

resource "google_secret_manager_secret" "db_pass_secret" {
  secret_id = "alloydb-db-pass"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_version" "db_pass_secret_version" {
  secret      = google_secret_manager_secret.db_pass_secret.id
  secret_data = local.db_password
}

resource "google_secret_manager_secret_iam_member" "secret_accessor" {
  secret_id = google_secret_manager_secret.db_pass_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.auth_demo_sa.email}"
}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  service            = each.value
  disable_on_destroy = false
}

# Service Account
resource "google_service_account" "auth_demo_sa" {
  account_id   = var.service_account_name
  display_name = "Auth Demo SA"
}

# AlloyDB Cluster
resource "google_alloydb_cluster" "rma_cluster" {
  cluster_id = var.cluster_id
  location   = var.region

  # Initial password, managed via variable or generated randomly
  initial_user {
    password = local.db_password
  }

  # Use default network as in the manual setup
  network_config {
    network = "projects/${var.project_id}/global/networks/default"
  }

  depends_on = [google_project_service.apis["alloydb.googleapis.com"]]
}

# AlloyDB Instance
resource "google_alloydb_instance" "rma_instance_1" {
  cluster       = google_alloydb_cluster.rma_cluster.name
  instance_id   = var.instance_id
  instance_type = "PRIMARY"

  machine_config {
    cpu_count = 2
  }

  network_config {
    enable_public_ip = true
  }

  depends_on = [google_alloydb_cluster.rma_cluster]
}

# Cloud Run Service
resource "google_cloud_run_service" "auth_issue_demo" {
  name     = var.cloud_run_service_name
  location = var.region

  template {
    spec {
      containers {
        image = var.cloud_run_image
        env {
          name  = "ALLOYDB_URI"
          value = "projects/${var.project_id}/locations/${var.region}/clusters/${var.cluster_id}/instances/${var.instance_id}"
        }
        env {
          name  = "DB_USER"
          value = "postgres"
        }
        env {
          name = "DB_PASS"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.db_pass_secret.secret_id
              key  = "latest"
            }
          }
        }
        env {
          name  = "USE_PUBLIC_IP"
          value = "true"
        }
      }
      service_account_name = google_service_account.auth_demo_sa.email
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.apis["run.googleapis.com"],
    google_alloydb_instance.rma_instance_1,
    google_secret_manager_secret_version.db_pass_secret_version,
    google_secret_manager_secret_iam_member.secret_accessor
  ]
}

# Allow unauthenticated access to Cloud Run service (matching --allow-unauthenticated)
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_service.auth_issue_demo.location
  project  = google_cloud_run_service.auth_issue_demo.project
  service  = google_cloud_run_service.auth_issue_demo.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
