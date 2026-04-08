import os
import vertexai
from vertexai.agent_engines import AdkApp, create
from google.adk.plugins.bigquery_agent_analytics_plugin import BigQueryAgentAnalyticsPlugin
from adk_agent_app.agent import get_root_agent
from dotenv import dotenv_values

# Config
config = dotenv_values(".env")
PROJECT_ID = config["PROJECT_ID"]
LOCATION = config["LOCATION"]
STAGING_BUCKET = config["STAGING_BUCKET"]
SERVICE_ACCOUNT = config["SERVICE_ACCOUNT"]
DATASET_ID = config["BIGQUERY_DATASET"]

def deploy():
    vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)
    
    # Create App
    app = AdkApp(
        agent=get_root_agent(),
        plugins=[BigQueryAgentAnalyticsPlugin(project_id=PROJECT_ID, dataset_id=DATASET_ID, table_id="agent_events")]
    )

    # Deploy
    print("Deploying Agent...")
    remote_app = create(
        app,
        display_name="Cymbal Bank Fraud Assitant",
        requirements=[line.strip() for line in open("requirements.txt") if line.strip() and not line.startswith("#")], 
        extra_packages=["./adk_agent_app"],
        env_vars={k:v for k,v in config.items() if k not in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION")},
        service_account=SERVICE_ACCOUNT 
    )
    
    endpoint_url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{remote_app.resource_name}:streamQuery"
    print(f"Deployed Resource Name: {remote_app.resource_name}")
    print("\n" + "="*80)
    print("Pub/Sub Push Endpoint URL:")
    print(endpoint_url)
    print("="*80 + "\n")
    
    with open("agent_endpoint.txt", "w") as f:
        f.write(endpoint_url)

if __name__ == "__main__":
    deploy()
