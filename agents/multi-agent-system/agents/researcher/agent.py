from google.adk.agents import Agent
from google.adk.tools.google_search_tool import google_search


MODEL = "gemini-2.5-pro"

# --- Researcher Agent ---
researcher = Agent(
    name="researcher",
    model=MODEL,
    description="Gathers information on a topic using Google Search.",
    instruction="""
    You are an expert researcher. Your goal is to find comprehensive and accurate information on the user's topic.
    Use the `google_search` tool to find relevant information.
    Summarize your findings clearly.
    If you receive feedback that your research is insufficient, use the feedback to refine your next search.
    """,
    tools=[google_search],
)

root_agent = researcher

