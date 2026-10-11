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

"""
/**
 * @file __init__.py
 * @description Package initializer for Module 3 ("Harden and secure") reference
 *   solutions covering Step 3a (`PreToolUse` lifecycle hooks), Step 3b (Sensitive
 *   PII & secret data scrubbing), and Step 3c (Human-in-the-Loop authorizations).
 *
 * Why: Exposes a unified package interface for Module 3 security guardrails so
 * verification tools (`verify_workspace.py`), unit tests (`test_module_3.py`),
 * and E2E test suites can inspect and import Step 3a, 3b, and 3c symbols cleanly.
 */
"""

from __future__ import annotations

from .step_3a_pre_tool_use_hooks import (
    ALLOWED_TOOLS,
    AUDIT_LOG,
    DEFAULT_ALLOWLIST,
    DEFAULT_TOOL_ALLOWLIST,
    FORBIDDEN_ARG_KEYS,
    HookDecision,
    MAX_ARG_LENGTH,
    PreToolUseGuard,
    PreToolUseHook,
    ToolAuthorizationError,
    ToolLifecycleGuard,
    before_tool_callback,
    check_tool_call,
    validate_tool_call,
    validate_tool_use,
)
from .step_3b_pii_scrubbing import (
    PII_PATTERNS,
    PIIScrubber,
    REDACTED_CC,
    REDACTED_EMAIL,
    REDACTED_PHONE,
    REDACTED_SECRET,
    REDACTED_SSN,
    ScrubResult,
    sanitize_pii,
    scrub_dict,
    scrub_payload,
    scrub_pii,
    scrub_sensitive_data,
    scrub_text,
)
from .step_3c_hitl_authorizations import (
    AFFIRMATIVE_RESPONSES,
    APPROVAL_PROMPT_MESSAGE,
    Context,
    Event,
    HITLWorkflowResult,
    RequestInput,
    approve_concept,
    evaluate_user_approval,
    execute_hitl_workflow,
    hitl_workflow,
    node,
    run_hitl_workflow,
    user_approval,
)

MODULE_ID: int = 3
MODULE_TITLE: str = "Harden and secure"
MODULE_3_STEPS: tuple[str, ...] = ("3a", "3b", "3c")

__all__ = [
    "AFFIRMATIVE_RESPONSES",
    "ALLOWED_TOOLS",
    "APPROVAL_PROMPT_MESSAGE",
    "AUDIT_LOG",
    "Context",
    "DEFAULT_ALLOWLIST",
    "DEFAULT_TOOL_ALLOWLIST",
    "Event",
    "FORBIDDEN_ARG_KEYS",
    "HITLWorkflowResult",
    "HookDecision",
    "MAX_ARG_LENGTH",
    "MODULE_3_STEPS",
    "MODULE_ID",
    "MODULE_TITLE",
    "PII_PATTERNS",
    "PIIScrubber",
    "PreToolUseGuard",
    "PreToolUseHook",
    "REDACTED_CC",
    "REDACTED_EMAIL",
    "REDACTED_PHONE",
    "REDACTED_SECRET",
    "REDACTED_SSN",
    "RequestInput",
    "ScrubResult",
    "ToolAuthorizationError",
    "ToolLifecycleGuard",
    "approve_concept",
    "before_tool_callback",
    "check_tool_call",
    "evaluate_user_approval",
    "execute_hitl_workflow",
    "hitl_workflow",
    "node",
    "run_hitl_workflow",
    "sanitize_pii",
    "scrub_dict",
    "scrub_payload",
    "scrub_pii",
    "scrub_sensitive_data",
    "scrub_text",
    "user_approval",
    "validate_tool_call",
    "validate_tool_use",
]
