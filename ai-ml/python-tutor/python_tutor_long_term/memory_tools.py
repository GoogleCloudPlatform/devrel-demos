from google.adk.tools import ToolContext
from typing import Dict, Any


async def search_memory(tool_context: ToolContext, query: str = "score") -> list:
    """
    Search Vertex AI memory bank for relevant information about the user's learning progress.
    The agent is instructed to pass the student's user_name as the query,
    as a temp. workaround to: https://github.com/google/adk-web/issues/49
    """
    try:
        search_results = await tool_context.search_memory(query)
        print(f"✅ SearchMemoryResponse: ")
        print(search_results)
        return search_results
    except Exception as e:
        print(f"❌ Error searching memory: {e}")
        import traceback
        traceback.print_exc()
        return []


def set_user_name(tool_context: ToolContext, name: str) -> Dict[str, Any]:
    """
    Set the user's name in the state for memory tracking.

    Args:
        tool_context: The tool context containing state
        name: The user's name to store

    Returns:
        Dictionary containing:
        - status: 'success' or 'error'
        - message: Confirmation or error message
        - user_name: The set user name (if successful)
    """
    state = tool_context.state

    # Clean and validate the name
    cleaned_name = name.strip().lower()

    if not cleaned_name or not cleaned_name.replace(" ", "").isalpha():
        return {
            "status": "error",
            "error_message": f"Invalid name '{name}'. Please provide a valid name containing only letters.",
        }

    state["user_name"] = cleaned_name
    print(f"✏️ Username set to: {cleaned_name}")

    return {
        "status": "success",
        "message": f"I've recorded your name as {cleaned_name}. Nice to meet you!",
        "user_name": cleaned_name,
    }
