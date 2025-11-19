import base64
from cloudevents.http import CloudEvent
from google.adk import runners
from google.cloud import pubsub_v1
from google.genai import types
import json
import logging
import uuid
from zookeeper_agent import root_agent

logging.basicConfig(
    level=logging.INFO,
    force=True,
)
logger = logging.getLogger(__name__)

runner = runners.InMemoryRunner(app_name='zoo_agent', agent=root_agent)

def _parse_pubsub_message(event: CloudEvent) -> dict:
    """Parse Pub/Sub message from Eventarc event."""
    if 'message' in event.data and 'data' in event.data['message']:
        encoded_data = event.data['message']['data']
        decoded_bytes = base64.b64decode(encoded_data)
        return json.loads(decoded_bytes.decode('utf-8'))
    else:
        raise ValueError('CloudEvent does not follow Pub/Sub message schema')

async def process_request(event: CloudEvent, topic_path: str) -> tuple[str, int]:
    """Process incoming Eventarc event with Pub/Sub message."""

    logger.info("👉 parse PubSub message from Eventarc event")
    pubsub_message = {}
    try:
        pubsub_message = _parse_pubsub_message(event)
    except Exception as e:
        logger.error(f"❌ error processing Pub/Sub message: {e}")
        return 'Error processing Pub/Sub message from Eventarc event', 400
    
    user_id = pubsub_message.get('user_id', 'pubsub')
    session_id = str(uuid.uuid4())
    logger.info(f"👉 create session for user:{user_id}, session:{session_id}")
    await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id, session_id=session_id
    )
    if 'prompt' not in pubsub_message and 'message' not in pubsub_message:
        return 'Need to have "prompt" or "message" keys in Pub/Sub message', 400
    data = pubsub_message['prompt'] if 'prompt' in pubsub_message else pubsub_message['message']
    message = types.Content(
        role='user',
        parts=[types.Part.from_text(text=data)]
    )
    logger.info(f"👉 Prompt the Zookeeper agent for '{data}'")
    response = ''
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
        ):
             if event.is_final_response():
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response += part.text
                elif event.actions and event.actions.escalate: # Handle potential errors/escalations
                    return f'Agent escalated: {event.error_message or 'No specific message.'}', 500
                break
    except Exception as e:
        logger.error(f"❌ Error invoking designated runner: {e}")
        return 'Error invoking designated runner', 500

    if topic_path == '':
        logger.info("👉 no reply topic configured, skip publishing response")
        logger.info(f"👉 response: {response}")
        return 'Response is logged but not published.', 200
    logger.info(f"👉 publish the response: '{response[:20]}'... to the {topic_path} topic")
    publisher = pubsub_v1.PublisherClient()
    response_payload = {
        'response': response,
        'session_id': session_id,
        'user_id': user_id,
    }
    payload = json.dumps(response_payload).encode('utf-8')
    future = publisher.publish(topic_path, data=payload)
    message_id = future.result()
    logger.info(f"👉 published with ID {message_id}")
    return 'Response is published to the reply topic successfully.', 200
