# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Subtask 5: Asynchronous Telemetry Publisher.
"""

import json
from google.cloud import pubsub_v1

class TelemetryService:
    def __init__(self, project_id: str, topic_id: str):
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_id)

    def publish_turn_event(self, event_data: dict):
        """
        Flushes conversation telemetry asynchronously to Pub/Sub.
        """
        payload = json.dumps(event_data).encode("utf-8")
        self.publisher.publish(self.topic_path, payload)
