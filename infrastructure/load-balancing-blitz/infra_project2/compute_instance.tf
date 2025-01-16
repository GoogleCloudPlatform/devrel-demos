/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
Google Cloud References:
* https://cloud.google.com/compute/docs/ip-addresses/reserve-static-external-ip-address

Hashicorp References:
* https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_instance
* https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_instance_template
* https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_instance_from_template
*/

resource "google_compute_instance_from_machine_image" "default" {
  for_each     = local.config.create_vms ? toset(local.config.vms) : toset([])
  provider     = google-beta
  name         = "vm-${each.key}"
  zone         = local.config.zone
  machine_type = "n1-standard-1"
  tags         = ["game", "web-server", "application"]

  network_interface {
    network    = "default"
    subnetwork = google_compute_subnetwork.default.name
    // static internal ip
    network_ip = google_compute_address.internal[each.key].address
    #    // static external ip
    #    access_config {
    #      nat_ip = google_compute_address.external[each.key].address
    #    }
  }

  source_machine_image = local.config.source_machine_image

  lifecycle {
    ignore_changes = [metadata]

  }
}


resource "google_compute_instance_from_machine_image" "warehouse" {
  for_each     = local.config.create_vms ? toset(local.config.wh-vms) : toset([])
  provider     = google-beta
  name         = "vm-${each.key}"
  zone         = local.config.zone
  machine_type = "n1-standard-1"
  tags         = ["game", "web-server", "warehouse", "wh"]

  network_interface {
    network    = "default"
    subnetwork = google_compute_subnetwork.default.name
    #    // static internal ip
    #    network_ip = google_compute_address.wh-internal[each.key].address
    #    access_config {
    #      // static external ip
    #      nat_ip = google_compute_address.wh-external[each.key].address
    #    }

  }

  source_machine_image = local.config.source_machine_image

  lifecycle {
    ignore_changes = [metadata]
  }
}

