from google.adk import Agent
from google.adk.tools import google_search  # The Google Search tool

import sys
sys.path.append("..")
from callback_logging import log_query_to_model, log_model_response


root_agent = Agent(
    # name: A unique name for the agent.
    name="google_search_agent",
    # description: A short description of the agent's purpose, so
    # other agents in a multi-agent system know when to call it.
    description="Answer questions using Google Search.",
    # model: The LLM model that the agent will use:
    model="gemini-2.0-flash-001",
    # instruction: Instructions (or the prompt) for the agent.
    instruction="You are an expert researcher. You stick to the facts.",
    # callbacks: Allow for you to run functions at certain points in
    # the agent's execution cycle. In this example, you will log the
    # request to the agent and its response.
    before_model_callback=log_query_to_model,
    after_model_callback=log_model_response,

    # tools: functions to enhance the model's capabilities.
    # Add the google_search tool below.
    tools=[google_search]
)
