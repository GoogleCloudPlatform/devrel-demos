resource "google_compute_router" "default" {
  name    = "lb-blitz-game-vms-router"
  region  = local.config.region
  network = "default"

  bgp {
    asn = 64514
  }
}

resource "google_compute_router_nat" "default" {
  name                               = "lb-blitz-game-vms-nat"
  router                             = google_compute_router.default.name
  region                             = local.config.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_PRIMARY_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}