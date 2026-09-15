# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import mimetypes
import os

import google.auth.transport.requests
import google.oauth2.id_token
import httpx
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.context import Context
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)
from google.adk.apps import App
from google.adk.events import Event, RequestInput
from google.adk.models import Gemini
from google.adk.workflow import JoinNode, Workflow, node
from google.genai import types

load_dotenv()

MODEL = "gemini-3.8-flash"

def _model() -> Gemini:
    return Gemini(
        model=MODEL,
        client_kwargs={"location": "global"},
        retry_options=types.HttpRetryOptions(attempts=3),
    )

## Configure visual-director RemoteA2aAgent agent below this comment
VISUAL_DIRECTOR_URL = os.getenv("VISUAL_DIRECTOR_URL", "http://localhost:8801")

## For deployment on Cloud Run
def _cloud_run_client() -> httpx.AsyncClient | None:
    """An httpx client that signs each request with a Cloud Run ID token.

    Cloud Run deploys private, so both the agent-card fetch and the A2A calls
    need one.
    """
    if not VISUAL_DIRECTOR_URL.startswith("https://"):
        return None

    async def sign(request: httpx.Request) -> None:
        token = await asyncio.to_thread(
            google.oauth2.id_token.fetch_id_token,
            google.auth.transport.requests.Request(),
            VISUAL_DIRECTOR_URL,
        )
        request.headers["Authorization"] = f"Bearer {token}"

    return httpx.AsyncClient(event_hooks={"request": [sign]}, timeout=600)

visual_director = RemoteA2aAgent(
    name="visual_director",
    description="Turns a campaign concept into art direction for one key visual.",
    agent_card=(
        f"{VISUAL_DIRECTOR_URL}/a2a/visual_director{AGENT_CARD_WELL_KNOWN_PATH}"
    ),
    httpx_client=_cloud_run_client(),
)

creative_director = Agent(
   name="creative_director",
   model=_model(),
   description="Turns a raw idea into a campaign concept.",
   instruction=(
      "You are the Creative Director. Turn the idea you are given into ONE "
      "punchy campaign concept line with the rationale explanation behind it."
   ),
   output_key="creative_director"
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

## Waits for every node wired into it, then hands their outputs on together.
assemble = JoinNode(name="assemble")

async def package(ctx: Context, node_input: dict):
   """Render the joined branches as the finished pitch."""
   empty = [name for name, value in node_input.items() if not value]
   if empty:
      raise ValueError(f"nothing reached the join from: {', '.join(empty)}")

   def _key_visual(ctx: Context) -> types.Blob | None:
      """The image the Visual Director sent back, or None if it sent none."""
      for event in reversed(ctx.session.events):
         if event.author != "visual_director" or not event.content:
               continue
         for part in event.content.parts or []:
               if part.inline_data and part.inline_data.data:
                  return part.inline_data
      return None

   image = _key_visual(ctx)
   if image is None:
      raise ValueError("the Visual Director returned art direction but no image")

   suffix = mimetypes.guess_extension(image.mime_type or "") or ".bin"
   filename = f"key_visual{suffix}"
   await ctx.save_artifact(filename, types.Part(inline_data=image))

   pitch = "\n\n".join(
      [
         f"CONCEPT\n{node_input['creative_director']}",
         f"COPY\n{node_input['copywriter']}",
         f"ART DIRECTION\n{node_input['visual_director']}",
         f"KEY VISUAL\n{filename}, {len(image.data)} bytes, {image.mime_type}",
      ]
   )
   yield Event(
      content=types.Content(
         role="model",
         parts=[types.Part(text=pitch), types.Part(inline_data=image)],
      )
   )
   yield Event(output=pitch)

@node(rerun_on_resume=False)
async def approve_concept(ctx: Context):
    yield RequestInput(
        message="Please approve the campaign concept (yes/no).",
        response_schema=str
    )

@node(rerun_on_resume=True)
async def user_approval(ctx: Context):
   user_response = await ctx.run_node(approve_concept)
   if str(user_response).lower() in ("yes", "y"):
      approved_concept = f"# Approved Concept\n\n{ctx.session.state['creative_director']}"
      yield Event(
         content=types.Content(
            role="model",
            parts=[types.Part(text=approved_concept)]
         )
      )
   else:
      raise ValueError("User rejected the concept")

root_agent = Workflow(
   name="pitch_generator",
   edges=[
        ("START", creative_director),
        (creative_director, user_approval, (copywriter, visual_director)),
        ((creative_director, copywriter, visual_director), assemble),
        (assemble, package),
    ],
)

app = App(
   root_agent=root_agent,
   name="pitch_generator",
)