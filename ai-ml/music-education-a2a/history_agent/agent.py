from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from tools import adk_wikipedia_tool, google_search_tool

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
    model="gemini-2.5-pro",
    name="historical_context_agent",
    instruction=agent_instruction,
    tools=[adk_wikipedia_tool, google_search_tool],
)
# Expose Historical Context agent with ADK's A2A wrapper
# (this will autogenerate the A2A Agent Card)
print("🚀 Exposing ADK agent with A2A...")
a2a_app = to_a2a(root_agent, port=8001)
