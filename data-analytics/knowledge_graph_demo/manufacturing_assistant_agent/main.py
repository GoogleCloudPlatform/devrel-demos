from agent import create_graph_agent
from google.adk.plugins.bigquery_agent_analytics_plugin import BigQueryAgentAnalyticsPlugin
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.apps import App
from google.genai import types
import uuid
import asyncio
import dotenv
import os
import sys

dotenv.load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "missing-project-id")
DATASET_ID = os.getenv("DATASET_ID")
TABLE_ID = os.getenv("AGENT_LOGS_TABLE_ID")
APP_NAME = "manufacturing_assistant"
USER_ID = "sample.user"


async def main(prompt: str):
    """Runs a conversation with the BigQuery agent using the ADK Runner."""

    root_agent = create_graph_agent()

    bq_logger_plugin = BigQueryAgentAnalyticsPlugin(
        project_id=PROJECT_ID, dataset_id=DATASET_ID, table_id=TABLE_ID
    )
    
    app = App(name=APP_NAME, root_agent=root_agent, plugins=[bq_logger_plugin])      
    
    runner = Runner(app=app, session_service=InMemorySessionService())
    
    try:
        session_id = f"{USER_ID}_{uuid.uuid4().hex[:8]}"

        my_session = await runner.session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )

        async for event in runner.run_async(
            user_id=USER_ID,
            new_message=types.Content(
                role="user", parts=[types.Part.from_text(text=prompt)]
            ),
            session_id=my_session.id,
        ):
            print(event)
            
            if event.content and event.content.parts and event.content.parts[0].text:
                print("------ agent response ------ \n")
                print(f"** {event.author}: {event.content.parts[0].text}")

    except Exception as e:
        print(f"Error in main: {e}")
    finally:
         await bq_logger_plugin.close()

if __name__ == "__main__":    
    # Suppress noisy async cleanup by redirecting stderr to null
    sys.stderr = open(os.devnull, 'w')
    
    prompts = [
       f"what can you tell me about my dataset {DATASET_ID} in project {PROJECT_ID}?",
       "Find customers who purchased products containing fiberglass",
       "Find the address of our Royal Soft Serve customer in BigQuery and then use the maps tools to find the closest recycling centre"
    ]
    for i, prompt in enumerate(prompts):        
        try:
            asyncio.run(main(prompt))
        except:
             pass
        