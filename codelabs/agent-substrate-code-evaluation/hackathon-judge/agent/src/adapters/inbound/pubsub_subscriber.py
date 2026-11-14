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

# src/adapters/inbound/pubsub_subscriber.py
import asyncio
import logging
from google.cloud import pubsub_v1
from src.core.ports.agent_service import AgentService
from src.core.ports.message_publisher import MessagePublisher
from src.core.models.message import AgentRequest

logger = logging.getLogger(__name__)

class BackgroundSubscriber:
    def __init__(self, agent_service: AgentService, publisher: MessagePublisher, project_id: str = None, subscription_id: str = None):
        self.agent_service = agent_service
        self.publisher = publisher
        self.project_id = project_id
        self.subscription_id = subscription_id
        self._running = False
        self._task = None
        self.subscriber = None
        self.streaming_pull_future = None
        self._loop = None

    async def process_raw_message(self, message_id: str, text: str, pubsub_message=None):
        try:
            logger.info(f"Processing message {message_id}")
            request = AgentRequest.model_validate_json(text)
            response = await self.agent_service.process_message(request)
            await self.publisher.publish(response)
            if pubsub_message:
                pubsub_message.ack()
            logger.info(f"Successfully processed and acked message {message_id}")
        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")
            if pubsub_message:
                pubsub_message.nack()

    def _callback(self, message):
        logger.info(f"Received message: {message.message_id}")
        text = message.data.decode("utf-8")
        
        # Schedule the async process_raw_message on the main event loop
        asyncio.run_coroutine_threadsafe(
            self.process_raw_message(message.message_id, text, message),
            self._loop
        )

    async def start(self):
        self._loop = asyncio.get_running_loop()
        if not self.project_id or not self.subscription_id:
            logger.info("No project_id or subscription_id provided. Starting in mock mode.")
            self._running = True
            self._task = asyncio.create_task(self._mock_listen_loop())
            return

        self.subscriber = pubsub_v1.SubscriberClient()
        subscription_path = self.subscriber.subscription_path(self.project_id, self.subscription_id)
        
        self.streaming_pull_future = self.subscriber.subscribe(
            subscription_path, callback=self._callback
        )
        logger.info(f"Background subscriber listening to {subscription_path}")

    async def stop(self):
        if self.streaming_pull_future:
            self.streaming_pull_future.cancel()
            self.subscriber.close()
            logger.info("Background subscriber stopped")
        elif self._task:
            self._running = False
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Mock subscriber stopped")

    async def _mock_listen_loop(self):
        while self._running:
            await asyncio.sleep(1)
