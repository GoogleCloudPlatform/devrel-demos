import platform
from google.adk.agents import Agent
from google.adk.tools import AgentTool, google_search
import osquery
import vertexai
from vertexai.preview import rag
import os

# --- Initialize Vertex AI ---
# This is needed for the custom RAG tool to function.
# It will use the credentials from the environment.
vertexai.init()

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

def schema_discovery_tool(query: str) -> str:
    """
    Searches a knowledge base of osquery table schemas to find the most
    relevant table and its schema for a given problem description,
    operating system, or table name.

    Args:
        query: A natural language query describing the problem or the
               table to find.
    Returns:
        A string containing the most relevant schema definitions.
    """
    corpus_name = os.environ.get("CORPUS_NAME")
    try:
        response = rag.retrieval_query(
            rag_corpora=[corpus_name],
            text=query,
        )
        # Correctly access the source URI via the 'source_uri' attribute
        formatted_response = "\n---\n".join(
            [f"Source URI: {res.source_uri}\nContent:\n{res.text}" for res in response.contexts.contexts]
        )
        return formatted_response if formatted_response else "No relevant schemas found."
    except Exception as e:
        return f"An error occurred while searching the schema database: {e}"


# --- Agent for Google Search ---
google_search_agent = Agent(
    name="google_search",
    instruction="You are a google search agent.",
    tools=[google_search],
    model="gemini-2.5-flash",
)
google_search_tool = AgentTool(
    agent=google_search_agent
)

# --- Root Agent ---
root_agent = Agent(
    name="tricorder",
    instruction=(
        f"You are an expert at diagnosing issues on {platform.system()} systems. "
        "Your primary goal is to use the osquery_tool to investigate and resolve user issues. "
        "Before using osquery_tool, you MUST first use the schema_discovery_tool "
        "to find the correct table and understand its schema. This will help you write "
        "accurate and effective queries. If you are unsure about a general IT or security "
        "concept, you may use the google_search_tool for clarification."
    ),
    tools=[
        osquery_tool,
        google_search_tool,
        schema_discovery_tool
    ],
    model="gemini-2.5-flash",
)