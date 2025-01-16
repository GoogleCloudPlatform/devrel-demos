resource "google_compute_address" "external" {
  for_each = toset(local.config.vms)
  name     = "external-static-ip-${each.key}"
}

resource "google_compute_address" "internal" {
  for_each     = toset(local.config.vms)
  name         = "internal-static-ip-${each.key}"
  address_type = "INTERNAL"
  subnetwork   = google_compute_subnetwork.default.name
}

resource "google_compute_address" "lb" {
  name         = "blitz-lb"
  address_type = "INTERNAL"
  subnetwork   = google_compute_subnetwork.default.name
}

#
## In future, warehouse machines dont need external ip
#resource "google_compute_address" "wh-external" {
#  for_each = toset(local.config.wh-vms)
#  name     = "external-static-ip-${each.key}"
#}
#
#
#resource "google_compute_address" "wh-internal" {
#  for_each     = toset(local.config.wh-vms)
#  name         = "internal-static-ip-${each.key}"
#  address_type = "INTERNAL"
#  subnetwork   = google_compute_subnetwork.default.name
#}
