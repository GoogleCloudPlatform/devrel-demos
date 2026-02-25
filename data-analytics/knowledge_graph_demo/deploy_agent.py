import os
import vertexai
from vertexai import agent_engines
from dotenv import load_dotenv
from google.adk.plugins.bigquery_agent_analytics_plugin import BigQueryAgentAnalyticsPlugin

# Load environment variables
load_dotenv("./manufacturing_assistant_agent/.env")

# --- Configuration Constants ---
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "missing-project-id")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
STAGING_BUCKET = os.getenv("STAGING_BUCKET", "gs://kg_demo_adk_staging_bucket")

# Application Config
MAPS_API_KEY = os.getenv('MAPS_API_KEY', "missing-maps-api-key")
DATASET_ID = os.getenv("DATASET_ID", "kg_demo")
AGENT_LOGS_TABLE_ID = os.getenv("AGENT_LOGS_TABLE_ID", "manufacturing_agent_logs")

# --- Deployment Dependencies ---
REQUIREMENTS = [
    "google-cloud-aiplatform[agent_engines,adk]==1.133.0", 
    "google-adk==1.22.1",
    "google-genai==1.59.0",
    "cloudpickle==3.1.2",
    "pydantic==2.12.5",
    "pydantic-settings==2.12.0",
    "google-cloud-bigquery",
    "google-auth",
    "python-dotenv"
]

def create_agent_app():
    """Creates the local agent app instance with plugins."""
    try:
        from manufacturing_assistant_agent.agent import create_graph_agent
    except ImportError:
        from agent import create_graph_agent

    # Create the agent instance by calling the factory function
    root_agent = create_graph_agent()
    
    bq_plugin = BigQueryAgentAnalyticsPlugin(
        project_id=PROJECT_ID,
        dataset_id=DATASET_ID,
        table_id=AGENT_LOGS_TABLE_ID
    )
    
    return agent_engines.AdkApp(agent=root_agent, plugins=[bq_plugin])

def deploy(agent_name: str, agent_desc: str):
    """Deploys the agent to Vertex AI, keeping the main logic clean."""
    
    print(f"Initializing Vertex AI for project: {PROJECT_ID}...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

    print("Building Agent App...")
    agent_app = create_agent_app()

    deployment_config = {
        "display_name": agent_name,
        "description": agent_desc,
        "requirements": REQUIREMENTS,
        "extra_packages": ["./manufacturing_assistant_agent"],
        "staging_bucket": STAGING_BUCKET,
        "env_vars": {
            "GOOGLE_GENAI_USE_VERTEXAI": "1",
            "MAPS_API_KEY": MAPS_API_KEY,
            "DATASET_ID": DATASET_ID,
            "AGENT_LOGS_TABLE_ID": AGENT_LOGS_TABLE_ID
        }
    }

    print("Submitting deployment job...")
    try:
        remote_agent = client.agent_engines.create(
            agent=agent_app,
            config=deployment_config
        )
        print(f"\n✅ Deployment Complete!")

        return remote_agent
    except Exception as e:
        print(f"\n❌ Deployment Failed: {e}")
        raise e

if __name__ == "__main__":
    deploy("Knowledge Agent", "ADK Knowledge Agent for BigQuery Knowledge Graph and Maps analytics")
