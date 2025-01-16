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
# Cloud Pub Sub
# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/pubsub_subscription

#
## Topic for storing score messages
#resource "google_pubsub_topic" "scores" {
#  // name = "game-scores"
#  name = local.config.send_pubsub_topic
#}
#
#resource "google_pubsub_subscription" "scores" {
#  // name  = "score-subscription"
#  name  = local.config.send_pubsub_subscription
#  topic = google_pubsub_topic.scores.id
#
#  ack_deadline_seconds = 50
#
#}
#
## Topic for storing score messages
#resource "google_pubsub_topic" "healthcheck" {
#  // name = "game-health"
#  name = local.config.receive_pubsub_topic_scores
#}
#
#resource "google_pubsub_subscription" "healthcheck" {
#  // name  = "process-healthcheck"
#  name  = local.config.receive_pubsub_subscription
#  topic = google_pubsub_topic.healthcheck.id
#
#  ack_deadline_seconds = 50
#
#}