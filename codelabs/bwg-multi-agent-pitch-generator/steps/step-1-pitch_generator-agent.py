import mimetypes
import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.context import Context
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)
from google.adk.apps import App
from google.adk.events.event import Event
from google.adk.models import Gemini
from google.adk.workflow import JoinNode, Workflow
from google.genai import types

load_dotenv()

MODEL = "gemini-3.8-flash"

def _model() -> Gemini:
    return Gemini(
        model=MODEL,
        client_kwargs={"location": "global"},
        retry_options=types.HttpRetryOptions(attempts=3),
    )

""" ⬇️ Configure visual-director RemoteA2aAgent agent below this comment """


creative_director = Agent(
   name="creative_director",
   model=_model(),
   description="Turns a raw idea into a campaign concept.",
   instruction=(
      "You are the Creative Director. Turn the idea you are given into ONE "
      "punchy campaign concept line with the rationale explanation behind it."
   ),
   output_key="creative_director",
)

copywriter = Agent(
   name="copywriter",
   model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
   description="Writes social copy for a campaign concept.",
   instruction=(
      "You are the Copywriter. Write ONE short social caption for the "
      "campaign concept you are given. Under 25 words."
   ),
)

""" Waits for every node wired into it, then hands their outputs on together."""
assemble = JoinNode(name="assemble")

def package(node_input: dict):
   """Render the joined branches as the finished pitch.
   """

   pitch = "\n\n".join(
      [
            f"CONCEPT\n{node_input['creative_director']}",
            f"COPY\n{node_input['copywriter']}",
      ]
   )
   """ The first event is what the user sees. The second is the node's output,
   which any downstream node would receive."""
   yield Event(content=types.Content(role="model", parts=[types.Part(text=pitch)]))
   yield Event(output=pitch)

""" we put creative_director before `assemble`  so that we can
   gather the `Concept` output at assemble"""
root_agent = Workflow(
   name="pitch_generator",
   edges=[
      ("START", creative_director),
      (creative_director, copywriter),
      ((creative_director, copywriter), assemble),
      (assemble, package),
   ],
)

app = App(
   root_agent=root_agent,
   name="pitch_generator",
)
