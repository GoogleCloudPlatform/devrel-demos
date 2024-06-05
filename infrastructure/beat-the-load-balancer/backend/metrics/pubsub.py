#!/usr/bin/env python

# Copyright 2024 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from dataclasses import dataclass

from google.cloud import pubsub_v1

project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "beat-the-load-balancer")
# _publisher_client = pubsub_v1.PublisherClient()

_path_prefix = __file__.rsplit(os.path.sep, 2)[0]
_file_path = "creds/beat-the-load-balancer-2d741c7f89ef.json"
# _publisher_client = pubsub_v1.PublisherClient()
_publisher_client = pubsub_v1.PublisherClient.from_service_account_json(
    os.path.join(
        __file__.rsplit(os.path.sep, 2)[0],
        _file_path,
    )
)


@dataclass
class PubSubTopic:
    health_check = _publisher_client.topic_path(project_id, "game_vm_health_check")
    score = _publisher_client.topic_path(project_id, "game_vm_score")
    game_record = _publisher_client.topic_path(project_id, "game_player_record")


def send_healthcheck_to_pubsub(encoded_json_data: bytes) -> str:
    future = _publisher_client.publish(PubSubTopic.health_check, encoded_json_data)
    return future.result(timeout=30)


def send_score_to_pubsub(encoded_score_data: bytes) -> str:
    future = _publisher_client.publish(PubSubTopic.score, encoded_score_data)
    return future.result(timeout=30)


def send_game_record_to_pubsub(encoded_game_data: bytes) -> str:
    future = _publisher_client.publish(PubSubTopic.game_record, encoded_game_data)
    return future.result(timeout=30)
