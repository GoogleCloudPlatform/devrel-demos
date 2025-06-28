import os
import sys
sys.path.append("..")
from callback_logging import log_query_to_model, log_model_response

from google.adk import Agent
from google.adk.tools.langchain_tool import LangchainTool # import
from google.adk.agents.callback_context import CallbackContext

from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

from dotenv import load_dotenv

# 1. Load environment variables from the agent directory's .env file
load_dotenv()
model_name = os.getenv("MODEL")

root_agent = Agent(
    name="lanchgain_tool_agent",
    model=model_name,
    description="Answers questions using Wikipedia.",
    before_model_callback=log_query_to_model,
    after_model_callback=log_model_response,
    instruction="""Research the topic suggested by the user.
    Share the information you have found with the user.""",
    # Add the LangChain Wikipedia tool below
    tools = [
        # Use the LangchainTool wrapper...
        LangchainTool(
            # to pass in a LangChain tool.
            # In this case, the WikipediaQueryRun tool,
            # which requires the WikipediaAPIWrapper as
            # part of the tool.
            tool=WikipediaQueryRun(
              api_wrapper=WikipediaAPIWrapper()
            )
        )
    ]
)