# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

provider "google" {
  project = var.project
  region  = var.region
}

###############
# Enable APIs #
###############

# Enable Compute API
resource "google_project_service" "compute_api" {
  project    = var.project
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

##################
# Compute Engine #
##################

resource "google_compute_network" "vpc" {
  project    = var.project
  name                    = "network"
  auto_create_subnetworks = false
  mtu                     = 1460
}

resource "google_compute_subnetwork" "default" {
  project    = var.project
  name          = "subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.region
  network       = google_compute_network.vpc_network.id
}

resource "google_compute_instance" "subnet" {
  project    = var.project
  name         = "node-virtual-machine"
  machine_type = "f1-micro"
  zone         = "${var.region}-a"
  tags         = ["ssh"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }
  # Install Flask
  metadata_startup_script = "sudo apt-get update; sudo apt-get install -yq nodejs npm rsync; npm install express"

  network_interface {
    subnetwork = google_compute_subnetwork.subnet.id
    access_config {}
  }
}

resource "google_compute_firewall" "ssh-firewall" {
  name = "allow-ssh"
  allow {
    ports    = ["22"]
    protocol = "tcp"
  }
  direction     = "INGRESS"
  network       = google_compute_network.vpc_network.id
  priority      = 1000
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["ssh"]
}

resource "google_compute_firewall" "node-firewall" {
  name    = "node-firewall"
  network = google_compute_network.vpc_network.id

  allow {
    protocol = "tcp"
    ports    = ["5000"]
  }
  source_ranges = ["0.0.0.0/0"]
}

##########
# Output #
##########

output "external-url" {
 value = join("",["http://",google_compute_instance.default.network_interface.0.access_config.0.nat_ip,":5000"])
}
