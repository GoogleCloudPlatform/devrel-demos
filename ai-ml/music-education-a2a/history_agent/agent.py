from google.adk.agents import Agent
from google.adk.tools.langchain_tool import LangchainTool

from run_a2a import adk_as_a2a
from tools import langchain_wikipedia_tool, google_search_tool


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
root_agent = Agent(
    model="gemini-2.5-pro",  # Keep gemini-2.5-pro as requested
    name="historical_context_agent",
    description="Agent that performs historical research using Wikipedia and Google Search",
    instruction=agent_instruction,
    tools=[LangchainTool(langchain_wikipedia_tool), google_search_tool],
)

a2a_app = adk_as_a2a(
    root_agent
)
