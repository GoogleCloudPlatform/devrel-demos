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

variable "region" {
  type        = string
  description = "Google Cloud project region"
  default     = "us-central1"
}

variable "project" {
  type        = string
  description = "Google Cloud project id"
}

variable "repo_owner" {
  type        = string
  description = "Connected Github repository owner in Cloud Build Triggers. (i.e GoogleCloudPlatform in GoogleCloudPlatform/train-to-cloud-city)"
}

variable "repo_name" {
  type        = string
  description = "Connected Github repository name in Cloud Build Triggers. (i.e train-to-cloud-city in GoogleCloudPlatform/train-to-cloud-city)"
}

