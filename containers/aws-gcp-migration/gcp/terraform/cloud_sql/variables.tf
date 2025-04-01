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

variable "source_database_host" {
  type = string
}

variable "source_database_port" {
  default = 5432
  type    = number
}

variable "source_database_password" {
  sensitive = true
  type      = string
}

variable "source_database_username" {
  sensitive = true
  type      = string
}

variable "destination_database_zone" {
  default = "us-central1-f"
  type    = string
}
