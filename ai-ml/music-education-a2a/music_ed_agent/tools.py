import os
import logging
import re
from google.adk.tools.langchain_tool import LangchainTool
from langchain_community.tools import YouTubeSearchTool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# https://python.langchain.com/docs/integrations/tools/youtube/
#  📹 YouTube Search Tool - LangChain 3p tool
youtube_search_tool_instance = YouTubeSearchTool()
adk_youtube_search_tool = LangchainTool(tool=youtube_search_tool_instance)


#  🌐 Wikipedia Search Tool - LangChain 3p tool
wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
adk_wikipedia_tool = LangchainTool(tool=wikipedia)
