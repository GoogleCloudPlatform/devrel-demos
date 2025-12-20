import platform
from google.adk.agents import Agent
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

# Create an agent and add the tool
root_agent = Agent(
    name="tricorder",
    instruction=(
        f"You are an expert at diagnosing issues on {platform.system()} systems. " +
        "Interpret the user request to your best capability and use " + 
        "the available tools to perform the diagnostic procedures. " +
        "You have the following tables available to you: " + 
        f"{osquery_tool('select name from osquery_registry where registry = "table"')}"
    ),
    tools=[osquery_tool],
    model="gemini-2.5-flash",
)
