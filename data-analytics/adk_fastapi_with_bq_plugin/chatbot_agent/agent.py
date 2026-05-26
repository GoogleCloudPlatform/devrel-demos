# chatbot_agent/agent.py
import os
from google.adk import Agent
from google.genai import types

# Load the model configuration from the environment
model_name = os.getenv("MODEL", "gemini-3.5-flash")

# Define the conversational chatbot agent
chatbot = Agent(
    name="chatbot",
    model=model_name,
    description="A friendly, helpful conversational chatbot assistant.",
    instruction="""
    You are a polite, helpful, and concise conversational assistant. 
    Engage in general conversation, answer questions, and help the user as best as you can.
    Keep your answers friendly and clear.
    """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
    )
)

# Alias the agent instance to root_agent so the ADK dynamic loader can find it
root_agent = chatbot
