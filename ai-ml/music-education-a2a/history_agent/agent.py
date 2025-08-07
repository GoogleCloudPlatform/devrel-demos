from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
import os
import requests
from history_agent.tools import adk_wikipedia_tool, google_search_tool


def get_cloud_run_url():
    """Construct Cloud Run URL from environment variables."""
    service_name = os.getenv("K_SERVICE")

    if not service_name:
        return "http://localhost:8080"  # Local development

    # Try to get project number from metadata service (Cloud Run)
    try:
        headers = {"Metadata-Flavor": "Google"}
        response = requests.get(
            "http://metadata.google.internal/computeMetadata/v1/project/numeric-project-id",
            headers=headers,
            timeout=1,
        )
        project_number = response.text
        region = os.getenv("GCP_REGION", "us-central1")
        return f"https://{service_name}-{project_number}.{region}.run.app"
    except:
        print("⚠️ Couldn't get Cloud Run service URL")
        return "http://localhost:8080"


agent_instruction = """
You are a history education agent that helps students learn about historical topics.

You will be given a topic as a text query. Your task is to search relevant knowledge bases for key, authoritative information about that topic.

For instance, if the topic is a person, look up biographical details about that person's life. If the topic is a historical event, research when and what happened. 

Always try to contextualize your response - for instance, what were the broader historical events, movements, or figures that may have influenced this topic? How did this topic or event impact history?

AVAILABLE TOOLS (KNOWLEDGE BASES): 
- Google Search (google_search_tool) 
- Wikipedia (adk_wikipedia_tool)

Don't provide too much information back to the user, just key info broken into bullet points. Use emojis to make your response more readable.  
"""

print("🔁 Initializing historical context agent...")

# Get the public URL
public_url = get_cloud_run_url()
print(f"👟 Agent Server URL: {public_url}")

# Create the agent with the correct URL
root_agent = Agent(
    model="gemini-2.5-pro",
    name="historical_context_agent",
    instruction=agent_instruction,
    tools=[adk_wikipedia_tool, google_search_tool],
)

# Use to_a2a to create a full A2A server with all necessary endpoints
print("🚀 Exposing ADK agent with A2A...")
a2a_app = to_a2a(root_agent, host="0.0.0.0", port=8080)
