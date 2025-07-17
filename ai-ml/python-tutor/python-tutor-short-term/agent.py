from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from typing import Optional
from tools.tools import (
    get_quiz_questions,
    start_quiz,
    submit_answer,
    get_current_question,
    get_quiz_status,
    reset_quiz,
)
from python_tutor_core.prompts import BASE_PROMPT, QUIZ_INSTRUCTIONS
from python_tutor_core.agent_utils import initialize_quiz_state


# Callback to initialize quiz state
# https://google.github.io/adk-docs/callbacks/types-of-callbacks/#before-agent-callback
def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """Initialize quiz state if not already present"""
    initialize_quiz_state(callback_context.state)
    return None


quiz_tools = [
    get_quiz_questions,
    start_quiz,
    submit_answer,
    get_current_question,
    get_quiz_status,
    reset_quiz,
]

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="python_tutor_short_term",
    instruction=BASE_PROMPT + QUIZ_INSTRUCTIONS,
    tools=quiz_tools,
    before_agent_callback=before_agent_callback,
)
