import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.agents.callback_context import CallbackContext


class LyriaPrompt(BaseModel):
    """Represents a music generation request in a semi-structured form.
    It is made for a music generation AI model called Lyria.
    """

    original_request: str = Field(
        description="User's original text prompt for music generation"
    )
    generation_config: types.LiveMusicGenerationConfig = Field(
        description="Parameters of music to be generated."
    )
    weighted_prompts: List[types.WeightedPrompt] = Field(
        description="""
        List of weighted prompts. Each prompt
        is an element or an attribute of the produced music piece,
        mapped to a relative weight. Weights cannot be 0.
        https://ai.google.dev/gemini-api/docs/music-generation#prompt-guide-lyria
    """
    )


def _clean_base_models(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Callback for cleaning up response schema for LLM requests
    """

    def _clean(data: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in data.copy().items():
            if key == "additionalProperties":
                data.pop(key)
            if isinstance(value, dict):
                data[key] = _clean(value)
        return data

    if llm_request.config and llm_request.config.response_schema:
        schema = llm_request.config.response_schema
        if isinstance(schema, types.Schema):
            schema = schema.model_dump()
        elif hasattr(schema, "model_json_schema"):
            schema = schema.model_json_schema()  # type: ignore
        elif not isinstance(schema, dict):
            schema = json.loads(str(schema))
        llm_request.config.response_schema = _clean(schema)
    else:
        return None


user_prompt_parser_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="UserPromptParser",
    description="Converts user's free text music prompt into a Lyria API request",
    global_instruction="""
        You are a music brainstorming agent, that transforms musicians' text ideas into snippets of music to use as inspiration for new compositions. 
        Your task is to understand user's request, parse it into a semi-structured form.
        Include suggested values for required parameters when the user doesn't specify them.
        You must split the idea between multiple weighted prompts, each with its own components, such as instrument, mood, performance instructions, etc.
""",
    output_schema=LyriaPrompt,
    output_key="lyria_prompt",
    before_model_callback=_clean_base_models,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)
