import os
import sys
from typing import Tuple, Optional
from google.cloud import modelarmor_v1


def _collect_config_and_inputs() -> Tuple[
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
]:
    """Collects configuration from environment variables and text from user input."""

    # 1. Collect configuration values as distinct variables
    project_id = os.environ.get("PROJECT_ID", "").strip()
    location_id = os.environ.get("LOCATION_ID", "").strip()
    user_prompt_template_id = os.environ.get("USER_PROMPT_TEMPLATE_ID", "").strip()
    response_template_id = os.environ.get("RESPONSE_TEMPLATE_ID", "").strip()

    # Graceful error handling: Check for any missing environment variables
    missing_vars = []
    if not project_id:
        missing_vars.append("PROJECT_ID")
    if not location_id:
        missing_vars.append("LOCATION_ID")
    if not user_prompt_template_id and not response_template_id:
        missing_vars.append("USER_PROMPT_TEMPLATE_ID or RESPONSE_TEMPLATE_ID")

    if missing_vars:
        print("\n[Error] Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables before running the script.")
        # Return None for all expected variables to indicate failure
        return None, None, None, None, None, None

    # 2. Collect input text
    print("\n--- Input Data ---")
    user_prompt_text = model_response_text = ""
    if user_prompt_template_id:
        user_prompt_text = input("Enter the user prompt to sanitize: ").strip()
    if response_template_id:
        model_response_text = input("Enter the model response to sanitize: ").strip()
        if not user_prompt_text:
            user_prompt_text = input(
                "[OPTIONAL] Enter the user prompt (it will not be sanitized): "
            ).strip()

    # Graceful error handling: Ensure input text is provided
    if (user_prompt_template_id and not user_prompt_text) or (
        response_template_id and not model_response_text
    ):
        print(
            "\n[Error] You need to input text to be used with user prompt and/or model response calls."
        )
        return None, None, None, None, None, None

    return (
        project_id,
        location_id,
        user_prompt_template_id,
        response_template_id,
        user_prompt_text,
        model_response_text,
    )


def sanitize_user_prompt(
    project_id: str, location_id: str, template_id: str, user_prompt_text: str
) -> None:
    """Initializes the client and invokes the sanitize_user_prompt API endpoint."""

    client_options = {"api_endpoint": f"modelarmor.{location_id}.rep.googleapis.com"}
    client = modelarmor_v1.ModelArmorClient(client_options=client_options)

    template_name = (
        f"projects/{project_id}/locations/{location_id}/templates/{template_id}"
    )

    prompt_request = modelarmor_v1.SanitizeUserPromptRequest(
        name=template_name,
        user_prompt_data=modelarmor_v1.DataItem(text=user_prompt_text),
    )

    print("\n--- 1. Sanitizing User Prompt ---")
    try:
        prompt_response = client.sanitize_user_prompt(request=prompt_request)
        print(prompt_response)
    except Exception as e:
        print(f"[API Error] Failed to sanitize user prompt:\n{e}")


def sanitize_model_response(
    project_id: str,
    location_id: str,
    template_id: str,
    model_response_text: str,
    user_prompt_text: str,
) -> None:
    """Initializes the client and invokes the sanitize_model_response API endpoint, using the user prompt for context."""

    client_options = {"api_endpoint": f"modelarmor.{location_id}.rep.googleapis.com"}
    client = modelarmor_v1.ModelArmorClient(client_options=client_options)

    template_name = (
        f"projects/{project_id}/locations/{location_id}/templates/{template_id}"
    )

    response_request = modelarmor_v1.SanitizeModelResponseRequest(
        name=template_name,
        model_response_data=modelarmor_v1.DataItem(text=model_response_text),
        user_prompt_data=modelarmor_v1.DataItem(text=user_prompt_text),
    )

    print("\n--- 2. Sanitizing Model Response ---")
    try:
        model_response = client.sanitize_model_response(request=response_request)
        print(model_response)
    except Exception as e:
        print(f"[API Error] Failed to sanitize model response:\n{e}")


def main() -> None:
    # Gather all necessary data first using distinct variables
    (
        project_id,
        location_id,
        user_prompt_template_id,
        response_template_id,
        user_prompt_text,
        model_response_text,
    ) = _collect_config_and_inputs()

    # If inputs failed validation (signaled by returning None for project_id), gracefully exit
    if (
        not project_id
        or not location_id
        or (not user_prompt_template_id and not response_template_id)
    ):
        printf("[Input Error]: Check environment variables setup.")
        sys.exit(1)

    # 1. Call the user prompt sanitization method
    if user_prompt_template_id and user_prompt_text:
        sanitize_user_prompt(
            project_id, location_id, user_prompt_template_id, user_prompt_text
        )

    # 2. Call the model response sanitization method (passing the user prompt as required)
    if response_template_id and model_response_text:
        sanitize_model_response(
            project_id,
            location_id,
            response_template_id,
            model_response_text,
            user_prompt_text,
        )


if __name__ == "__main__":
    main()
