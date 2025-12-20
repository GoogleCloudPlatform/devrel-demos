import platform
from google.adk.agents import Agent
from google.adk.tools import AgentTool
from google.adk.tools import google_search
import osquery

def osquery_tool(query: str) -> str:
    """
    A tool for querying osquery.

    Args:
        query: The osquery query to execute.

    Returns:
        The result of the osquery query.
    """
    try:
        instance = osquery.SpawnInstance()
        instance.open()
        result = instance.client.query(query)
        return str(result.response)
    except Exception as e:
        return str(e)

google_search_agent = Agent(
    name="google_search",
    instruction="You are a google search agent.",
    tools=[google_search],
    model="gemini-2.5-flash",
)

google_search_tool = AgentTool(
    agent=google_search_agent
)

# Create an agent and add the tool
root_agent = Agent(
    name="tricorder",
    instruction=(
        f"You are an expert at diagnosing issues on {platform.system()} systems. " +
        "Interpret the user request to your best capability and use " +
        "the available tools to perform the diagnostic procedures. " +
        "You have the following tables available to you: " +
        f"{osquery_tool('select name from osquery_registry where registry = "table"')}" +
        "You also have a google search tool available to you."
    ),
    tools=[
        osquery_tool,
        google_search_tool
    ],
    model="gemini-2.5-flash",
)
