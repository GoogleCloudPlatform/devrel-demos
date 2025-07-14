from typing import Dict, Any

def initialize_quiz_state(state: Dict[str, Any], with_memory: bool = False):
    """
    Initializes the quiz state in the provided state dictionary.

    Args:
        state: The state dictionary to initialize.
        with_memory: Whether to initialize memory-related state.
    """
    if "quiz_initialized" not in state:
        state["quiz_initialized"] = True
        state["current_question_index"] = 0
        state["correct_answers"] = 0
        state["total_answered"] = 0
        state["score_percentage"] = 0
        state["quiz_started"] = False
        if with_memory:
            state["user_name"] = None
        print("[Callback] Initialized quiz state")
