# Copyright 2025 Google LLC
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


resource "google_vertex_ai_index" "default" {
  display_name = "index-${local.unique_str}"
  description  = "Index for storing document embeddings"
  metadata {

    # Note: The index config should be customized based on your model.
    config {
      dimensions                  = 1536
      approximate_neighbors_count = 0
      distance_measure_type       = "DOT_PRODUCT_DISTANCE"
      algorithm_config {
        brute_force_config {}
      }
    }
  }
}

resource "google_vertex_ai_index_endpoint" "default" {
  display_name = "Index endpoint"
  region       = var.region
}

resource "google_vertex_ai_index_endpoint_deployed_index" "default" {
  index_endpoint    = google_vertex_ai_index_endpoint.default.id
  deployed_index_id = "deployed_endpoint_${local.unique_str}"
  index             = google_vertex_ai_index.default.id

  # Note: The deployed index should be customized based on optimization
  #       and performance requirements.
  dedicated_resources {
    machine_spec {
      machine_type = "n1-standard-16"
    }
    min_replica_count = 1
  }

  # Design consideration: Query scaling (used instead of 'dedicated_resources')
  # automatic_resources {
  #   max_replica_count = 2
  # }

  depends_on = [module.project_services]
}

