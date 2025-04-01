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

locals {
  container_image_repository_fully_qualified_hostname = "${google_artifact_registry_repository.container_image_repository.location}-docker.pkg.dev"
  container_image_repository_name                     = "${google_artifact_registry_repository.container_image_repository.project}/${google_artifact_registry_repository.container_image_repository.repository_id}"
}

output "container_image_repository_fully_qualified_hostname" {
  description = "Fully qualified name of the container image repository."
  value       = local.container_image_repository_fully_qualified_hostname
}

output "container_image_repository_name" {
  description = "Container image repository name."
  value       = local.container_image_repository_name
}
