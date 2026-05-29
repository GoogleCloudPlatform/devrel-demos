# Copyright 2026 Google LLC
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

# src/adapters/outbound/pubsub_publisher.py
from src.core.ports.message_publisher import MessagePublisher
from src.core.models.message import AgentResponse
from google.cloud import pubsub_v1
import logging
import asyncio

logger = logging.getLogger(__name__)

class MockPubSubPublisherAdapter(MessagePublisher):
    def __init__(self):
        self.published_messages = []

    async def publish(self, response: AgentResponse) -> None:
        logger.info(f"Mock publishing: {response.overall_comments}")
        self.published_messages.append(response)

class PubSubPublisherAdapter(MessagePublisher):
    def __init__(self, project_id: str, topic_id: str):
        self.project_id = project_id
        self.topic_id = topic_id
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_id)

    async def publish(self, response: AgentResponse) -> None:
        data_str = response.model_dump_json()
        data_bytes = data_str.encode("utf-8")
        
        # Publish returns a future
        future = self.publisher.publish(self.topic_path, data=data_bytes)
        
        # Await the synchronous future result in an executor so we don't block the event loop
        loop = asyncio.get_running_loop()
        message_id = await loop.run_in_executor(None, future.result)
        logger.info(f"Published response for task {response.task_id} to {self.topic_id} (Pub/Sub msg ID: {message_id})")
