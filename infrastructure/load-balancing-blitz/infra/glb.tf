
resource "google_compute_instance_group" "default" {
  name        = "blitz-umig"
  description = "bltiz-umig for LB Warehouse worker instances"
  zone        = local.config.zone

  instances = [
    google_compute_instance_from_machine_image.warehouse["wh91"].id,
    google_compute_instance_from_machine_image.warehouse["wh92"].id,
    google_compute_instance_from_machine_image.warehouse["wh93"].id,
    google_compute_instance_from_machine_image.warehouse["wh94"].id,
  ]
  #
  #  named_port {
  #    name = "http"
  #    port = 80
  #  }
  named_port {
    name = "http"
    port = 8000
  }
}

resource "google_compute_region_health_check" "default" {
  name   = "health-check"
  region = local.config.region
  http_health_check {
    port = 8000
  }
}

resource "google_compute_region_backend_service" "default" {
  name                  = "blitz-umig-backend-service"
  provider              = google-beta
  region                = local.config.region
  protocol              = "HTTP"
  load_balancing_scheme = "INTERNAL_MANAGED"
  timeout_sec           = 10
  health_checks         = [google_compute_region_health_check.default.id]
  locality_lb_policy    = "ROUND_ROBIN"
  backend {
    group           = google_compute_instance_group.default.id
    balancing_mode  = "RATE" # Possible values are: UTILIZATION, RATE, CONNECTION.
    capacity_scaler = 1
    max_rate        = 2111222000 # max value is INT32

  }
}


# HTTP target proxy
resource "google_compute_region_target_http_proxy" "default" {
  name     = "blitz-umig-http-proxy"
  provider = google-beta
  region   = local.config.region
  url_map  = google_compute_region_url_map.default.id
}

# URL map
resource "google_compute_region_url_map" "default" {
  name            = "blitz-umig-url-map"
  provider        = google-beta
  region          = local.config.region
  default_service = google_compute_region_backend_service.default.id
}


# forwarding rule
resource "google_compute_forwarding_rule" "default" {
  name                  = "blitz-forwarding-rule"
  provider              = google-beta
  region                = local.config.region
  depends_on            = [google_compute_subnetwork.proxy_subnet]
  ip_protocol           = "TCP"
  ip_address            = google_compute_address.lb.id
  load_balancing_scheme = "INTERNAL_MANAGED"
  port_range            = "8000"
  target                = google_compute_region_target_http_proxy.default.id
  network               = "default"
  subnetwork            = google_compute_subnetwork.default.id
  network_tier          = "PREMIUM"
}

# proxy-only subnet
resource "google_compute_subnetwork" "proxy_subnet" {
  name          = "blitz-proxy-subnet"
  provider      = google-beta
  ip_cidr_range = "10.10.0.0/24"
  region        = local.config.region
  purpose       = "REGIONAL_MANAGED_PROXY"
  role          = "ACTIVE"
  network       = "default"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_region_backend_service#locality_lb_policy
# https://github.com/terraform-google-modules/terraform-docs-samples/blob/main/lb/internal_http_lb_with_mig_backend/main.tf
# https://github.com/terraform-google-modules/terraform-docs-samples/blob/main/lb/internal_http_lb_with_mig_backend/main.tf
