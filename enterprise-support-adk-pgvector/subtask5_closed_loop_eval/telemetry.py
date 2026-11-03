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
