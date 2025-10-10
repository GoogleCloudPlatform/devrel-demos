import os
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.memory import VertexAiMemoryBankService
from google.genai import types
from typing import Optional
from .tools.tools import (
    get_quiz_questions,
    start_quiz,
    submit_answer,
    get_current_question,
    get_quiz_status,
    reset_quiz,
)
from .python_tutor_core.prompts import (
    BASE_PROMPT,
    MEMORY_INSTRUCTIONS,
    QUIZ_INSTRUCTIONS,
)
from .python_tutor_core.agent_utils import initialize_quiz_state
from .memory_tools import search_memory, set_user_name


# Callback to initialize quiz state and detect username
def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """Initialize quiz state and detect user name from messages"""
    state = callback_context.state
    initialize_quiz_state(state, with_memory=True)

    # Try to extract user name from the current message if we don't have it yet
    if state.get("user_name") is None:
        # Get the current user message from the invocation context
        if hasattr(callback_context, "_invocation_context"):
            inv_ctx = callback_context._invocation_context

            # Check if there's a current user message
            if hasattr(inv_ctx, "user_message") and inv_ctx.user_message:
                user_text = (
                    inv_ctx.user_message.text.lower()
                    if hasattr(inv_ctx.user_message, "text")
                    else ""
                )

                # Look for name patterns
                name_patterns = [
                    "my name is ",
                    "i'm ",
                    "i am ",
                    "call me ",
                    "name's ",
                    "this is ",
                    "it's ",
                ]

                for pattern in name_patterns:
                    if pattern in user_text:
                        parts = user_text.split(pattern, 1)
                        if len(parts) > 1:
                            # Extract the name part
                            remaining_text = parts[1]
                            # Take first word after pattern
                            name_part = (
                                remaining_text.split()[0]
                                if remaining_text.split()
                                else ""
                            )

                            # Clean up punctuation
                            name_part = (
                                name_part.replace(".", "")
                                .replace(",", "")
                                .replace("!", "")
                                .replace("?", "")
                                .replace("'", "")
                                .replace('"', "")
                            )

                            # Basic validation - ensure it's a valid name
                            if name_part and len(name_part) > 1 and name_part.isalpha():
                                state["user_name"] = name_part.lower()
                                print(
                                    f"🎯 Detected and set user name: {state['user_name']}"
                                )
                                break

    return None


# Source: https://github.com/serkanh/adk-with-memorybank/blob/main/agents/memory_assistant/agent.py
async def auto_save_to_memory_callback(callback_context):
    """Automatically save completed sessions to memory bank using default session user_id"""
    try:
        session_id = None

        # Extract session information from invocation context
        if hasattr(callback_context, "_invocation_context"):
            inv_ctx = callback_context._invocation_context

            # Extract session ID
            if hasattr(inv_ctx, "session") and hasattr(inv_ctx.session, "id"):
                session_id = inv_ctx.session.id

        # Get the session from the invocation context
        session = callback_context._invocation_context.session

        if not session_id:
            print("⚠️ No Session ID found in callback context, skipping memory save")
            return

        # Initialize memory service
        agent_engine_id = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID")
        if not agent_engine_id:
            print("⚠️ Agent Engine ID not set, cannot save to memory")
            return

        memory_service = VertexAiMemoryBankService(
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            agent_engine_id=agent_engine_id,
        )

        # Check if session has meaningful content
        has_content = False
        content_count = 0

        if hasattr(session, "events") and session.events:
            content_count = len(session.events)
            has_content = content_count >= 2  # At least user message + agent response
        elif hasattr(session, "contents") and session.contents:
            content_count = len(session.contents)
            has_content = content_count >= 2

        if not has_content:
            print("📭 Session has no meaningful content, skipping memory save")
            return

        await memory_service.add_session_to_memory(session)
        print(f"🧠 Session auto-saved to memory bank")

    except Exception as e:
        print(f"⚠️ Error auto-saving to memory: {e}")
        import traceback
        traceback.print_exc()

enhanced_quiz_tools = [
    get_quiz_questions,
    start_quiz,
    submit_answer,
    get_current_question,
    get_quiz_status,
    reset_quiz,
    search_memory,
    set_user_name,
]

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="python_tutor_long_term",
    instruction=BASE_PROMPT + MEMORY_INSTRUCTIONS + QUIZ_INSTRUCTIONS,
    tools=enhanced_quiz_tools,
    before_agent_callback=before_agent_callback,
    after_agent_callback=auto_save_to_memory_callback,
)
