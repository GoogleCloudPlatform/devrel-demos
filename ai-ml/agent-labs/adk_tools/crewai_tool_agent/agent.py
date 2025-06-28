import os
import sys
sys.path.append("..")
from callback_logging import log_query_to_model, log_model_response

from dotenv import load_dotenv
from google.genai import types
from google.adk import Agent
from google.adk.tools.crewai_tool import CrewaiTool
from crewai_tools import FileWriterTool


# 1. Load environment variables from the agent directory's .env file
load_dotenv()
model_name = os.getenv("MODEL")

root_agent = Agent(
    name="crewai_tool_agent",
    model=model_name,
    description="Agent to write files.",
    instruction="Write files as requested by the user.",
    generate_content_config=types.GenerateContentConfig(
        temperature=0
    ),
    before_model_callback=log_query_to_model,
    after_model_callback=log_model_response,    
    # Add the CrewAI FileWriterTool below
    tools = [CrewaiTool(
        name="file_writer_tool",
        description=(
            "Writes a file to disk when run with a"
            "filename, content, overwrite set to 'true',"
            "and an optional directory"
        ),
        tool=FileWriterTool()
    )]
)