# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

# Model Armor imports
from google.cloud import modelarmor_v1
from google.api_core.client_options import ClientOptions


class ModelArmorGuard:
    """
    Model Armor security guard that provides callbacks for LlmAgent.

    Unlike plugins (which require Runner registration and don't work with
    `adk web`), this class provides standalone callback functions that can
    be passed directly to LlmAgent's before_model_callback and after_model_callback.

    Usage:
        guard = ModelArmorGuard(template_name="projects/.../templates/...")

        agent = LlmAgent(
            model="gemini-2.5-flash",
            before_model_callback=guard.before_model_callback,
            after_model_callback=guard.after_model_callback,
        )
    """

    def __init__(
        self,
        template_name: str,
        location: str = "us-west1",
        block_on_match: bool = True,
    ):
        """
        Initialize the Model Armor Guard.

        Args:
            template_name: Full resource name of the Model Armor template
                          (e.g., "projects/my-project/locations/us-central1/templates/my-template")
            location: Google Cloud region where Model Armor is deployed
            block_on_match: If True, block requests when threats detected.
                           If False, log warnings but allow through.
        """
        self.template_name = template_name
        self.location = location
        self.block_on_match = block_on_match

        # TODO 1: Initialize the Model Armor client
        self.client = modelarmor_v1.ModelArmorClient(
            transport="rest",
            client_options=ClientOptions(
                api_endpoint=f"modelarmor.{location}.rep.googleapis.com"
            ),
        )

        print(f"[ModelArmorGuard] ✅ Initialized with template: {template_name}")

    def _get_matched_filters(self, result) -> list[str]:
        """
        Extract filter names that detected threats from a sanitization result.

        Args:
            result: SanitizeUserPromptResponse or SanitizeModelResponseResponse

        Returns:
            List of filter names that matched (e.g., ['pi_and_jailbreak', 'sdp'])
        """
        matched_filters = []

        if result is None:
            return matched_filters

        # Navigate to filter_results
        try:
            filter_results = dict(result.sanitization_result.filter_results)
        except (AttributeError, TypeError):
            return matched_filters

        # Mapping of filter names to their corresponding result attribute names
        filter_attr_mapping = {
            "csam": "csam_filter_filter_result",
            "malicious_uris": "malicious_uri_filter_result",
            "pi_and_jailbreak": "pi_and_jailbreak_filter_result",
            "rai": "rai_filter_result",
            "sdp": "sdp_filter_result",
            "virus_scan": "virus_scan_filter_result",
        }

        for filter_name, filter_obj in filter_results.items():
            # Get the appropriate attribute name for this filter
            attr_name = filter_attr_mapping.get(filter_name)

            if not attr_name:
                # Try to construct the attribute name if not in mapping
                if filter_name == "malicious_uris":
                    attr_name = "malicious_uri_filter_result"
                else:
                    attr_name = f"{filter_name}_filter_result"

            # Get the actual filter result
            if hasattr(filter_obj, attr_name):
                filter_result = getattr(filter_obj, attr_name)

                # Special handling for SDP (has inspect_result wrapper)
                if filter_name == "sdp" and hasattr(filter_result, "inspect_result"):
                    if hasattr(filter_result.inspect_result, "match_state"):
                        if (
                            filter_result.inspect_result.match_state.name
                            == "MATCH_FOUND"
                        ):
                            matched_filters.append("sdp")

                # Special handling for RAI (has subcategories)
                elif filter_name == "rai":
                    # Check main RAI match state
                    if hasattr(filter_result, "match_state"):
                        if filter_result.match_state.name == "MATCH_FOUND":
                            matched_filters.append("rai")

                    # Check RAI subcategories
                    if hasattr(filter_result, "rai_filter_type_results"):
                        for sub_result in filter_result.rai_filter_type_results:
                            if hasattr(sub_result, "key") and hasattr(
                                sub_result, "value"
                            ):
                                if hasattr(sub_result.value, "match_state"):
                                    if (
                                        sub_result.value.match_state.name
                                        == "MATCH_FOUND"
                                    ):
                                        matched_filters.append(f"rai:{sub_result.key}")

                # Standard filters (pi_and_jailbreak, malicious_uris, etc.)
                else:
                    if hasattr(filter_result, "match_state"):
                        if filter_result.match_state.name == "MATCH_FOUND":
                            matched_filters.append(filter_name)

        return matched_filters

    def _extract_user_text(self, llm_request: LlmRequest) -> str:
        """Extract the user's text from the LLM request."""
        try:
            if llm_request.contents:
                for content in reversed(llm_request.contents):
                    if content.role == "user":
                        for part in content.parts:
                            if hasattr(part, "text") and part.text:
                                return part.text
        except Exception as e:
            print(f"[ModelArmorGuard] Error extracting user text: {e}")
        return ""

    def _extract_model_text(self, llm_response: LlmResponse) -> str:
        """Extract the model's text from the LLM response."""
        try:
            if llm_response.content and llm_response.content.parts:
                for part in llm_response.content.parts:
                    if hasattr(part, "text") and part.text:
                        return part.text
        except Exception as e:
            print(f"[ModelArmorGuard] Error extracting model text: {e}")
        return ""

    async def before_model_callback(
        self,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> Optional[LlmResponse]:
        """
        Callback called BEFORE the LLM processes the request.

        This sanitizes user prompts to detect:
        - Prompt injection attacks
        - Sensitive data in user input
        - Harmful content

        Args:
            callback_context: Context with session state and invocation info
            llm_request: The request about to be sent to the LLM

        Returns:
            None: Allow the request to proceed to the LLM
            LlmResponse: Block the request and return this response instead
        """
        # TODO 2: Extract user text from the request
        user_text = self._extract_user_text(llm_request)
        if not user_text:
            return None

        print(f"[ModelArmorGuard] 🔍 Screening user prompt: '{user_text[:80]}...'")

        try:
            # TODO 3: Call Model Armor to sanitize the user prompt
            sanitize_request = modelarmor_v1.SanitizeUserPromptRequest(
                name=self.template_name,
                user_prompt_data=modelarmor_v1.DataItem(text=user_text),
            )
            result = self.client.sanitize_user_prompt(request=sanitize_request)

            # TODO 4: Check for matched filters and block if needed
            matched_filters = self._get_matched_filters(result)

            if matched_filters and self.block_on_match:
                print(
                    f"[ModelArmorGuard] 🛡️ BLOCKED - Threats detected: {matched_filters}"
                )

                # Create user-friendly message based on threat type
                if "pi_and_jailbreak" in matched_filters:
                    message = (
                        "I apologize, but I cannot process this request. "
                        "Your message appears to contain instructions that could "
                        "compromise my safety guidelines. Please rephrase your question."
                    )
                elif "sdp" in matched_filters:
                    message = (
                        "I noticed your message contains sensitive personal information "
                        "(like SSN or credit card numbers). For your security, I cannot "
                        "process requests containing such data. Please remove the sensitive "
                        "information and try again."
                    )
                elif any(f.startswith("rai") for f in matched_filters):
                    message = (
                        "I apologize, but I cannot respond to this type of request. "
                        "Please rephrase your question in a respectful manner, and "
                        "I'll be happy to help."
                    )
                else:
                    message = (
                        "I apologize, but I cannot process this request due to "
                        "security concerns. Please rephrase your question."
                    )

                return LlmResponse(
                    content=types.Content(
                        role="model", parts=[types.Part.from_text(text=message)]
                    )
                )

            print(f"[ModelArmorGuard] ✅ User prompt passed security screening")

        except Exception as e:
            print(f"[ModelArmorGuard] ⚠️ Error during prompt sanitization: {e}")
            # On error, allow request through but log the issue

        return None

    async def after_model_callback(
        self,
        callback_context: CallbackContext,
        llm_response: LlmResponse,
    ) -> Optional[LlmResponse]:
        """
        Callback called AFTER the LLM generates a response.

        This sanitizes model outputs to detect:
        - Accidentally leaked sensitive data
        - Harmful content in model response
        - Malicious URLs in response

        Args:
            callback_context: Context with session state and invocation info
            llm_response: The response from the LLM

        Returns:
            None: Allow the response to return to the user
            LlmResponse: Replace the response with this sanitized version
        """
        # TODO 5: Extract model text from the response
        model_text = self._extract_model_text(llm_response)
        if not model_text:
            return None

        print(f"[ModelArmorGuard] 🔍 Screening model response: '{model_text[:80]}...'")

        try:
            # TODO 6: Call Model Armor to sanitize the model response
            sanitize_request = modelarmor_v1.SanitizeModelResponseRequest(
                name=self.template_name,
                model_response_data=modelarmor_v1.DataItem(text=model_text),
            )
            result = self.client.sanitize_model_response(request=sanitize_request)

            # TODO 7: Check for matched filters and sanitize if needed
            matched_filters = self._get_matched_filters(result)

            if matched_filters and self.block_on_match:
                print(
                    f"[ModelArmorGuard] 🛡️ Response sanitized - Issues detected: {matched_filters}"
                )

                message = (
                    "I apologize, but my response was filtered for security reasons. "
                    "Could you please rephrase your question? I'm here to help with "
                    "your customer service needs."
                )

                return LlmResponse(
                    content=types.Content(
                        role="model", parts=[types.Part.from_text(text=message)]
                    )
                )

            print(f"[ModelArmorGuard] ✅ Model response passed security screening")

        except Exception as e:
            print(f"[ModelArmorGuard] ⚠️ Error during response sanitization: {e}")

        return None


# =============================================================================
# Factory function for easy guard creation
# =============================================================================


def create_model_armor_guard(
    project_id: str = None,
    location: str = None,
    template_name: str = None,
) -> ModelArmorGuard:
    """
    Create a ModelArmorGuard with configuration from environment variables.

    Environment variables:
        GOOGLE_CLOUD_PROJECT: GCP project ID
        GOOGLE_CLOUD_LOCATION: Region (default: us-west1)
        TEMPLATE_NAME: Full Model Armor template resource name

    Returns:
        Configured ModelArmorGuard instance
    """
    project_id = (
        project_id
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("PROJECT_ID")
    )
    location = (
        location
        or os.environ.get("GOOGLE_CLOUD_LOCATION")
        or os.environ.get("LOCATION", "us-west1")
    )
    template_name = template_name or os.environ.get("TEMPLATE_NAME")

    if not template_name:
        raise ValueError(
            "TEMPLATE_NAME environment variable not set. "
            "Run setup/create_template.py first."
        )

    return ModelArmorGuard(
        template_name=template_name,
        location=location,
        block_on_match=True,
    )
