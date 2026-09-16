import mimetypes
from pathlib import Path

from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.skills import load_skill_from_dir
from google.adk.tools import ToolContext
from google.adk.tools.skill_toolset import SkillToolset
from google.genai import types
MODEL = "gemini-3.8-flash"

## Configure the `brand-guidelines` skill for the agent
BRAND_SKILL = load_skill_from_dir(Path(__file__).parent / "skills" / "brand-guidelines")

## Add definition of `generate_key_visual` tool below this comment
async def generate_key_visual(art_direction: str, tool_context: ToolContext) -> dict:
    """Render the art direction as the campaign's key visual.

    Args:
       art_direction: The art direction to render, in full.

    Returns:
       The saved artifact's filename, version, size and media type.
    """
    IMAGE_MODEL = "gemini-3.1-flash-lite-image"

    response = await genai.Client(location="global").aio.models.generate_content(
       model=IMAGE_MODEL, contents=art_direction
    )

    ## The image arrives as inline bytes on one of the response parts.
    image = next(
       (
          part.inline_data
          for part in response.candidates[0].content.parts or []
          if part.inline_data
       ),
       None,
    )
    if image is None:
       raise ValueError(f"{IMAGE_MODEL} returned no image for: {art_direction[:120]}")

    filename = "key_visual" + (
       mimetypes.guess_extension(image.mime_type or "") or ".bin"
    )
    version = await tool_context.save_artifact(filename, types.Part(inline_data=image))

    ## Return the artifact filename and version
    return {
       "filename": filename,
       "version": version,
       "bytes": len(image.data),
       "mime_type": image.mime_type,
    }

root_agent = Agent(
    name="visual_director",
    model=Gemini(
        model=MODEL,
        client_kwargs={"location": "global"},
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Turns a campaign concept into art direction and a key visual.",
    instruction="""You are the Visual Director on a campaign pitch team.

    Call `load_skill` for `brand-guidelines` before you write anything. The house
    style is not optional and it is not in this prompt.

    You are given a campaign concept. Then, in order:

    1. Write art direction for ONE key visual that sells it, obeying the brand
    guidelines: subject, composition, lighting, color, mood. Three or four
    sentences.
    2. Call `generate_key_visual` with exactly that art direction.

    Your final reply is the art direction itself and nothing else. No preamble, no
    alternatives, no questions back. Do not mention the skill, the tool, or the
    image file — the image travels on its own.""",
    tools=[
        SkillToolset(skills=[BRAND_SKILL]),
        ## Supply the `generate_key_visual` tool below this comment
        generate_key_visual,
    ],
)

app = App(
    root_agent=root_agent,
    name="visual_director",
)
