from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any

quiz = [
    (
        """Which statement about Python dictionaries is TRUE?
        A) Dictionary keys must be strings
        B) Dictionaries maintain the order of insertion (Python 3.7+)
        C) A dictionary can have duplicate keys
        D) Dictionary values must be immutable""",
        "B",
    ),
    (
        """What will be the output of the following code?

        my_dict = {"a": 1, "b": 2, "c": 3}
        my_dict["b"] = 5
        my_dict["d"] = 4
        print(len(my_dict))

        A) 3
        B) 5
        C) 4
        D) Error""",
        "C",
    ),
    (
        """Let's say that:

        scores = {"Alice": 90, "Bob": 85}

        Which of the following code snippets will NOT raise an error?
        A) print(scores.get("Charlie"))
        B) print(scores["Charlie"])
        C) print(scores.pop("Charlie"))
        D) del scores["Charlie"]""",
        "A",
    ),
    (
        """What will be the output of the following code?

        def modify_dict(d):
            d["new_key"] = 100
            d = {"completely": "different"}

        my_dict = {"original": 42}
        modify_dict(my_dict)
        print(my_dict)

        A) {"completely": "different"}
        B) {"completely": "different", "new_key": 100}
        C) {"original": 42}
        D) {"original": 42, "new_key": 100}""",
        "D",
    ),
]


def get_quiz_questions() -> Dict[str, Any]:
    """
    Get all quiz questions for the Python dictionaries quiz.

    Returns:
        Dictionary containing:
        - total_questions: Total number of questions in the quiz
        - questions: List of all question texts
    """
    return {
        "status": "success",
        "total_questions": len(quiz),
        "questions": [q[0] for q in quiz],
    }


def start_quiz(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Start the Python dictionaries quiz. Resets all progress and begins from question 1.

    Returns:
        Dictionary containing:
        - status: 'started' if successful
        - first_question: The first question text
        - question_number: Current question number (1)
        - total_questions: Total number of questions
    """
    state = tool_context.state

    # Reset/initialize quiz state
    state["quiz_started"] = True
    state["current_question_index"] = 0
    state["correct_answers"] = 0
    state["total_answered"] = 0
    state["score_percentage"] = 0

    if quiz:
        return {
            "status": "started",
            "first_question": quiz[0][0],
            "question_number": 1,
            "total_questions": len(quiz),
        }
    return {"status": "error", "error_message": "No questions available"}


def submit_answer(tool_context: ToolContext, answer: str) -> Dict[str, Any]:
    """
    Submit an answer for the current quiz question.

    Args:
        answer: The user's answer to the current question

    Returns:
        Dictionary containing:
        - status: 'success' or 'error'
        - is_correct: Whether the answer was correct
        - correct_answer: The correct answer
        - current_score: Current percentage score
        - questions_remaining: Number of questions left
        - next_question: Next question text (if available)
        - quiz_complete: True if all questions answered
    """
    state = tool_context.state

    # Check if quiz has started
    if not state.get("quiz_started", False):
        return {
            "status": "error",
            "error_message": "Quiz not started. Please start the quiz first.",
        }

    i = state.get("current_question_index", 0)

    # Check if quiz is already complete
    if i >= len(quiz):
        return {
            "status": "error",
            "error_message": "Quiz already completed",
            "final_score": state.get("score_percentage", 0),
            "correct": state.get("correct_answers", 0),
            "total": state.get("total_answered", 0),
        }

    # Get correct answer and check if user's answer is correct
    correct_answer = quiz[i][1]
    is_correct = answer.strip().lower() == correct_answer.strip().lower()

    # Update state
    state["total_answered"] = state.get("total_answered", 0) + 1
    if is_correct:
        state["correct_answers"] = state.get("correct_answers", 0) + 1

    # Calculate percentage
    total = state["total_answered"]
    correct = state["correct_answers"]
    state["score_percentage"] = int((correct / total) * 100) if total > 0 else 0

    # Move to next question
    state["current_question_index"] = i + 1

    # Prepare response
    response = {
        "status": "success",
        "is_correct": is_correct,
        "correct_answer": correct_answer,
        "explanation": f"The correct answer is: {correct_answer}",
        "current_score": state["score_percentage"],
        "questions_answered": state["total_answered"],
        "questions_remaining": len(quiz) - state["current_question_index"],
    }

    # Add next question if available
    if state["current_question_index"] < len(quiz):
        response["next_question"] = quiz[state["current_question_index"]][0]
        response["next_question_number"] = state["current_question_index"] + 1
    else:
        response["quiz_complete"] = True
        response["final_score"] = state["score_percentage"]
        response["total_correct"] = state["correct_answers"]
        response["total_questions"] = len(quiz)

    return response


def get_current_question(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the current question in the quiz.

    Returns:
        Dictionary containing:
        - status: 'success' or 'error'
        - question: Current question text
        - question_number: Current question number
        - total_questions: Total number of questions
    """
    state = tool_context.state

    if not state.get("quiz_started", False):
        return {
            "status": "error",
            "error_message": "Quiz not started. Please start the quiz first.",
        }

    i = state.get("current_question_index", 0)
    if i < len(quiz):
        return {
            "status": "success",
            "question": quiz[i][0],
            "question_number": i + 1,
            "total_questions": len(quiz),
        }
    return {
        "status": "error",
        "error_message": "No current question - quiz may be complete",
    }


def get_quiz_status(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the current status of the quiz including score and progress.

    Returns:
        Dictionary containing:
        - quiz_started: Whether quiz has been started
        - current_question_index: Index of current question (0-based)
        - questions_answered: Number of questions answered
        - correct_answers: Number of correct answers
        - score_percentage: Current percentage score
        - questions_remaining: Number of questions left
        - total_questions: Total number of questions
    """
    state = tool_context.state

    return {
        "status": "success",
        "quiz_started": state.get("quiz_started", False),
        "current_question_index": state.get("current_question_index", 0),
        "questions_answered": state.get("total_answered", 0),
        "correct_answers": state.get("correct_answers", 0),
        "score_percentage": state.get("score_percentage", 0),
        "questions_remaining": len(quiz) - state.get("current_question_index", 0),
        "total_questions": len(quiz),
    }


def reset_quiz(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Reset the quiz to start over from the beginning.

    Returns:
        Dictionary containing:
        - status: 'success'
        - message: Confirmation message
    """
    state = tool_context.state

    state["quiz_started"] = False
    state["current_question_index"] = 0
    state["correct_answers"] = 0
    state["total_answered"] = 0
    state["score_percentage"] = 0

    return {
        "status": "success",
        "message": "Quiz has been reset. You can start again whenever you're ready.",
    }
