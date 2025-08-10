import logging
from google.adk.tools.langchain_tool import LangchainTool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


#  🌐 Wikipedia Search Tool - LangChain 3p tool
langchain_wikipedia_tool = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
adk_wikipedia_tool = LangchainTool(tool=langchain_wikipedia_tool)


# 🔍 Google Search - wrap in agent tool
google_search_agent = Agent(
    model="gemini-2.5-pro",
    name="search_agent",
    instruction="""
    You are a web searching specialist, focused on finding information about classical music.
    """,
    tools=[google_search],
)

google_search_tool = AgentTool(google_search_agent)
