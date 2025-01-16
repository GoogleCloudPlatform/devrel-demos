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

# All created VM will have prefix 'vm-'
#   If the vm name is xyz then VM name is 'vm-xyz'
locals {
  config = jsondecode(file("${path.module}/config.json"))
}


resource "google_compute_firewall" "default" {
  name          = "tcp-proxy-fw-allow-health-check"
  description   = "firewall allow access from health check ranges"
  provider      = google
  direction     = "INGRESS"
  network       = "default" # google_compute_network.default.id
  source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]
  allow {
    protocol = "tcp"
  }
  target_tags = ["game"]
}

resource "google_compute_firewall" "flaskapp" {
  name          = "allow-http-server"
  description   = "Allow incoming traffic on the game server instances."
  provider      = google
  direction     = "INGRESS"
  network       = "default"
  source_ranges = ["0.0.0.0/0"]
  allow {
    protocol = "tcp"
    ports    = ["80", "8000", "8080", "5000-5050"]
  }
  target_tags = ["game", "web-server"]
}

resource "google_compute_subnetwork" "default" {
  name          = "game-subnet2"
  ip_cidr_range = "10.2.0.0/16"
  region        = "us-central1"
  network       = "default"
  secondary_ip_range {
    range_name    = "game-subnet-range2"
    ip_cidr_range = "192.168.10.0/24"
  }
}


