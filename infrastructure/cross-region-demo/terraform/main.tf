resource "google_cloud_run_v2_service" "backend" {
  name     = "two-tier-backend"
  location = var.region
  project  = var.project_id

  template {
    service_account = google_service_account.backend_sa.email
    containers {
      image = var.backend_image
      env {
        name  = "DEPLOY_ID"
        value = var.revision_id
      }
      env {
        name  = "BUCKET_NAME"
        value = google_storage_bucket.bucket_central.name
      }
      env {
        name  = "DEST_BUCKET_NAME"
        value = google_storage_bucket.bucket_east4.name
      }
      ports {
        container_port = 8080
      }
    }
  }
}

resource "google_cloud_run_v2_service" "backend_east4" {
  name     = "two-tier-backend-east4"
  location = "us-east4"
  project  = var.project_id

  template {
    service_account = google_service_account.backend_sa.email
    containers {
      image = var.backend_image
      env {
        name  = "DEPLOY_ID"
        value = var.revision_id
      }
      env {
        name  = "BUCKET_NAME"
        value = google_storage_bucket.bucket_east4.name
      }
      env {
        name  = "DEST_BUCKET_NAME"
        value = google_storage_bucket.bucket_europe.name
      }
      ports {
        container_port = 8080
      }
    }
  }
}

resource "google_cloud_run_v2_service" "backend_europe_west1" {
  name     = "two-tier-backend-europe-west1"
  location = "europe-west1"
  project  = var.project_id

  template {
    service_account = google_service_account.backend_sa.email
    containers {
      image = var.backend_image
      env {
        name  = "DEPLOY_ID"
        value = var.revision_id
      }
      env {
        name  = "BUCKET_NAME"
        value = google_storage_bucket.bucket_europe.name
      }
      env {
        name  = "DEST_BUCKET_NAME"
        value = google_storage_bucket.bucket_central.name
      }
      ports {
        container_port = 8080
      }
    }
  }
}

resource "google_cloud_run_v2_service" "frontend" {
  name     = "two-tier-frontend"
  location = var.region
  project  = var.project_id

  template {
    service_account = google_service_account.frontend_sa.email
    containers {
      image = var.frontend_image
      env {
        name  = "BACKEND_URL"
        value = google_cloud_run_v2_service.backend_europe_west1.uri
      }
      env {
        name  = "DEPLOY_ID"
        value = var.revision_id
      }
      ports {
        container_port = 8080
      }
    }
  }

  depends_on = [google_cloud_run_v2_service.backend_europe_west1]
}

resource "google_project_service" "cloudscheduler" {
  project            = var.project_id
  service            = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

resource "google_cloud_scheduler_job" "batch_ping" {
  name        = "batch-ping-job"
  description = "Perpetual batch ping for max requests and size"
  schedule    = "* * * * *"
  time_zone   = "UTC"
  project     = var.project_id
  region      = var.region

  http_target {
    http_method = "GET"
    uri         = "${google_cloud_run_v2_service.frontend.uri}/api/batch-ping?count=50&size=524288&mode=gcs"

    oidc_token {
      service_account_email = google_service_account.scheduler_sa.email
    }
  }

  depends_on = [google_project_service.cloudscheduler]
}

resource "google_storage_bucket" "bucket_central" {
  name          = "${var.project_id}-bucket-us-central1"
  location      = "us-central1"
  project       = var.project_id
  force_destroy = true
}

resource "google_storage_bucket" "bucket_east4" {
  name          = "${var.project_id}-bucket-us-east4"
  location      = "us-east4"
  project       = var.project_id
  force_destroy = true
}

resource "google_storage_bucket" "bucket_europe" {
  name          = "${var.project_id}-bucket-europe-west1"
  location      = "europe-west1"
  project       = var.project_id
  force_destroy = true
}

output "frontend_url" {
  value = google_cloud_run_v2_service.frontend.uri
}

resource "google_service_account" "backend_sa" {
  account_id   = "backend-runner"
  display_name = "Backend Cloud Run Service Account"
  project      = var.project_id
}

resource "google_service_account" "frontend_sa" {
  account_id   = "frontend-runner"
  display_name = "Frontend Cloud Run Service Account"
  project      = var.project_id
}

resource "google_service_account" "scheduler_sa" {
  account_id   = "batch-ping-scheduler"
  display_name = "Batch Ping Cloud Scheduler Service Account"
  project      = var.project_id
}

# Allow anyone to call the frontend
resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  location = google_cloud_run_v2_service.frontend.location
  project  = google_cloud_run_v2_service.frontend.project
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Only allow the frontend service account to call the backend
resource "google_cloud_run_v2_service_iam_member" "backend_restricted" {
  location = google_cloud_run_v2_service.backend.location
  project  = google_cloud_run_v2_service.backend.project
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.frontend_sa.email}"
}

# Allow the scheduler to call the frontend
resource "google_cloud_run_v2_service_iam_member" "scheduler_invoke_frontend" {
  location = google_cloud_run_v2_service.frontend.location
  project  = google_cloud_run_v2_service.frontend.project
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_sa.email}"
}

# Only allow the frontend service account to call the new backend east4
resource "google_cloud_run_v2_service_iam_member" "backend_east4_restricted" {
  location = google_cloud_run_v2_service.backend_east4.location
  project  = google_cloud_run_v2_service.backend_east4.project
  name     = google_cloud_run_v2_service.backend_east4.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.frontend_sa.email}"
}
# Only allow the frontend service account to call the new backend europe-west1
resource "google_cloud_run_v2_service_iam_member" "backend_europe_west1_restricted" {
  location = google_cloud_run_v2_service.backend_europe_west1.location
  project  = google_cloud_run_v2_service.backend_europe_west1.project
  name     = google_cloud_run_v2_service.backend_europe_west1.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.frontend_sa.email}"
}

resource "google_storage_bucket_iam_member" "backend_storage_central" {
  bucket = google_storage_bucket.bucket_central.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.backend_sa.email}"
}

resource "google_storage_bucket_iam_member" "backend_storage_east4" {
  bucket = google_storage_bucket.bucket_east4.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.backend_sa.email}"
}

resource "google_storage_bucket_iam_member" "backend_storage_europe" {
  bucket = google_storage_bucket.bucket_europe.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.backend_sa.email}"
}
