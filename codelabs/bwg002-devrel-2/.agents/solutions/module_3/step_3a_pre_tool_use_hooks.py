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
 * @file step_3a_pre_tool_use_hooks.py
 * @description Module 3 Step 3a reference solution implementing ADK `PreToolUse`
 *   lifecycle hooks to enforce tool allowlists, block unauthorized tools, and
 *   validate tool arguments against path traversal, prompt injection, oversized
 *   inputs, and forbidden safety-override flags.
 *
 * Why: Without deterministic pre-execution guardrails, an LLM agent could be
 * manipulated via prompt injection into invoking unauthorized tools (e.g.,
 * `exec_shell`, `delete_bucket`), traversing outside its skill directory
 * (`../../etc/passwd`), or passing unsafe override parameters (`bypass_safety`).
 * Enforcing a `PreToolUse` hook before every tool call provides a fail-closed
 * security boundary and a structured audit trail (`docs/outline.md` §5.1).
 */
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Iterable

DEFAULT_TOOL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "load_skill",
        "generate_key_visual",
    }
)

ALLOWED_TOOLS: set[str] = set(DEFAULT_TOOL_ALLOWLIST)
DEFAULT_ALLOWLIST: set[str] = set(DEFAULT_TOOL_ALLOWLIST)

MAX_ARG_LENGTH: int = 4096

FORBIDDEN_ARG_KEYS: frozenset[str] = frozenset(
    {
        "bypass_safety",
        "override_brand_guidelines",
        "disable_guardrails",
        "allow_unsafe",
        "skip_auth",
        "ignore_policy",
        "raw_exec",
        "shell",
        "sudo",
    }
)

PATH_SENSITIVE_ARG_KEYS: frozenset[str] = frozenset(
    {
        "skill_name",
        "filename",
        "path",
        "file_path",
        "output_path",
        "directory",
        "skill_dir",
    }
)

PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions",
        re.IGNORECASE,
    ),
    re.compile(
        r"disregard\s+(?:all\s+)?(?:previous|prior|above)\s+instructions",
        re.IGNORECASE,
    ),
    re.compile(
        r"forget\s+(?:all\s+)?(?:previous|prior|above)\s+instructions",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:reveal|output|print|show|leak|dump)\s+(?:your\s+|the\s+)?system\s+(?:prompt|instructions)",
        re.IGNORECASE,
    ),
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[\s*system\s*override\s*\]", re.IGNORECASE),
    re.compile(
        r"\b(?:jailbreak|do\s+anything\s+now|dan\s+mode)\b",
        re.IGNORECASE,
    ),
)

AUDIT_LOG: list[dict[str, Any]] = []


class ToolAuthorizationError(PermissionError, ValueError):
    """
    /**
     * Exception raised when a `PreToolUse` lifecycle hook blocks a tool invocation
     * while configured in `raise_on_block=True` enforcement mode.
     *
     * Why: Subclasses both `PermissionError` and `ValueError` so callers catching
     * either standard Python authorization or validation exceptions can handle
     * blocked tool invocations uniformly while inspecting `.tool_name`,
     * `.violation_type`, and `.audit_event`.
     */
    """

    def __init__(
        self,
        message: str,
        *,
        tool_name: str = "",
        violation_type: str = "unauthorized_tool",
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        """
        /**
         * Initialize the tool authorization exception with structured audit metadata.
         *
         * Why: Captures the offending tool name, violation classification, and audit
         * trail entry alongside the human-readable error message.
         *
         * @param message Human-readable explanation of why the tool call was blocked.
         * @param tool_name Name of the tool that triggered the violation.
         * @param violation_type Machine-readable violation category string.
         * @param audit_event Associated audit log entry dictionary.
         */
        """
        super().__init__(message)
        self.tool_name = tool_name
        self.violation_type = violation_type
        self.audit_event = dict(audit_event or {})


@dataclass
class HookDecision:
    """
    /**
     * Structured result returned by `PreToolUseHook.validate_tool_call`.
     *
     * Why: Provides a rich, inspectable decision object supporting attribute access
     * (`decision.allowed`, `decision.is_allowed`, `decision.permitted`,
     * `decision.reason`, `decision.violation_type`), boolean truthiness
     * (`if decision:`), and dictionary access (`decision["allowed"]`) for seamless
     * integration with ADK callbacks and test harnesses.
     */
    """

    allowed: bool
    tool_name: str
    sanitized_args: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    violation_type: str | None = None
    audit_event: dict[str, Any] = field(default_factory=dict)

    @property
    def is_allowed(self) -> bool:
        """
        /**
         * Alias property returning whether the tool invocation is permitted.
         *
         * Why: Supports callers and test suites inspecting `decision.is_allowed`.
         *
         * @return `True` if the tool call passed all checks, `False` otherwise.
         */
        """
        return self.allowed

    @property
    def permitted(self) -> bool:
        """
        /**
         * Alias property returning whether the tool invocation is permitted.
         *
         * Why: Supports callers inspecting `decision.permitted`.
         *
         * @return `True` if permitted, `False` otherwise.
         */
        """
        return self.allowed

    @property
    def event(self) -> dict[str, Any]:
        """
        /**
         * Return the structured audit event recorded for this hook evaluation.
         *
         * Why: Allows observability pipelines to extract the audit record directly
         * from the returned `HookDecision`.
         *
         * @return Dictionary representing the recorded audit event.
         */
        """
        return self.audit_event

    def to_dict(self) -> dict[str, Any]:
        """
        /**
         * Serialize the hook decision into a plain JSON-compatible dictionary.
         *
         * Why: Enables structured logging, API serialization, and `extract_field`
         * inspection in E2E tests.
         *
         * @return Dictionary containing decision fields.
         */
        """
        return {
            "allowed": self.allowed,
            "is_allowed": self.allowed,
            "permitted": self.allowed,
            "tool_name": self.tool_name,
            "sanitized_args": copy.deepcopy(self.sanitized_args),
            "reason": self.reason,
            "violation_type": self.violation_type,
            "audit_event": dict(self.audit_event),
        }

    def __bool__(self) -> bool:
        """
        /**
         * Evaluate truthiness of the decision based on `self.allowed`.
         *
         * Why: Allows concise `if hook.validate_tool_call(...):` checks in agent code.
         *
         * @return `True` when `self.allowed` is `True`.
         */
        """
        return self.allowed

    def __getitem__(self, key: str) -> Any:
        """
        /**
         * Support dictionary-style key lookup (`decision["allowed"]`).
         *
         * Why: Allows callers treating the decision as a `dict` to read fields cleanly.
         *
         * @param key Field name to retrieve.
         * @return Field value.
         */
        """
        data = self.to_dict()
        if key in data:
            return data[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        """
        /**
         * Support `.get(key, default)` dictionary-style lookup on `HookDecision`.
         *
         * Why: Ensures compatibility with dictionary consumer code.
         *
         * @param key Field name to retrieve.
         * @param default Fallback value if `key` is absent.
         * @return Field value or `default`.
         */
        """
        return self.to_dict().get(key, default)

    def __contains__(self, key: object) -> bool:
        """
        /**
         * Support `key in decision` membership checks.
         *
         * Why: Completes the mapping protocol for dictionary-style callers.
         *
         * @param key Key to check.
         * @return `True` if `key` is in the serialized decision dictionary.
         */
        """
        return key in self.to_dict()


class PreToolUseHook:
    """
    /**
     * Stateful ADK `PreToolUse` lifecycle guard enforcing tool allowlists, parameter
     * sanitization, path-traversal prevention, and prompt-injection blocking.
     *
     * Why: Centralizes pre-tool security policy enforcement and maintains an
     * instance-level (`self.audit_log`) and module-level (`AUDIT_LOG`) audit trail
     * of every authorized and blocked tool invocation (`docs/outline.md` §5.1).
     */
    """

    def __init__(
        self,
        allowlist: Iterable[str] | None = None,
        *,
        allowed_tools: Iterable[str] | None = None,
        max_arg_length: int = MAX_ARG_LENGTH,
        raise_on_block: bool = False,
    ) -> None:
        """
        /**
         * Initialize the `PreToolUseHook` with a configurable tool allowlist and argument cap.
         *
         * Why: Allows individual specialist agents to restrict their permitted tool
         * surface area (e.g., `load_skill` only vs. `load_skill` + `generate_key_visual`)
         * while defaulting to `DEFAULT_TOOL_ALLOWLIST`.
         *
         * @param allowlist Optional iterable of permitted tool names.
         * @param allowed_tools Optional keyword alias for `allowlist`.
         * @param max_arg_length Maximum character length permitted for any string argument.
         * @param raise_on_block Whether blocked calls should raise `ToolAuthorizationError`.
         */
        """
        resolved = allowlist if allowlist is not None else allowed_tools
        if resolved is None:
            self.allowlist: set[str] = set(DEFAULT_TOOL_ALLOWLIST)
        else:
            self.allowlist = {
                str(item).strip() for item in resolved if str(item).strip()
            }
        self.allowed_tools: set[str] = self.allowlist
        self.max_arg_length = int(max_arg_length)
        self.raise_on_block = bool(raise_on_block)
        self.audit_log: list[dict[str, Any]] = []
        self.audit_trail: list[dict[str, Any]] = self.audit_log
        self.events: list[dict[str, Any]] = self.audit_log

    def _record_audit_event(
        self,
        *,
        tool_name: str,
        allowed: bool,
        reason: str,
        violation_type: str | None,
        tool_args: dict[str, Any],
    ) -> dict[str, Any]:
        """
        /**
         * Record a structured security telemetry event in both the instance and module logs.
         *
         * Why: Guarantees every tool evaluation—whether permitted or denied—is
         * traceable for security auditing and governance verification.
         */
        """
        event: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool_name,
            "allowed": allowed,
            "reason": reason,
            "violation_type": violation_type,
            "arg_keys": sorted(str(k) for k in tool_args.keys()),
        }
        self.audit_log.append(event)
        AUDIT_LOG.append(event)
        return event

    def _inspect_value(
        self,
        key_name: str,
        value: Any,
    ) -> tuple[bool, str | None, str]:
        """
        /**
         * Recursively inspect a parameter value for length limits, path traversal, and
         * prompt injection patterns.
         *
         * Why: Attackers may nest malicious payloads inside dictionaries or lists;
         * recursive inspection ensures no parameter escapes validation while allowing
         * benign PII redaction placeholders (`[REDACTED_EMAIL]`, etc.).
         */
        """
        if isinstance(value, str):
            if len(value) > self.max_arg_length:
                return (
                    False,
                    "oversized_parameter",
                    (
                        f"Parameter {key_name!r} length ({len(value)}) exceeds maximum "
                        f"allowed length of {self.max_arg_length} characters."
                    ),
                )
            lower_val = value.lower()
            if (
                ".." in value
                or "/etc/" in lower_val
                or "\\\\" in value
                or "\\" in value
                or "\x00" in value
                or (
                    key_name.lower() in PATH_SENSITIVE_ARG_KEYS
                    and value.strip().startswith("/")
                )
            ):
                return (
                    False,
                    "path_traversal",
                    f"Path traversal or unauthorized file path detected in parameter {key_name!r}.",
                )
            for pattern in PROMPT_INJECTION_PATTERNS:
                if pattern.search(value):
                    return (
                        False,
                        "prompt_injection",
                        f"Prompt injection pattern detected in parameter {key_name!r}.",
                    )
            return True, None, ""

        if isinstance(value, dict):
            for sub_key, sub_val in value.items():
                clean_sub_key = str(sub_key).strip().lower()
                if (
                    clean_sub_key in FORBIDDEN_ARG_KEYS
                    or clean_sub_key.startswith("bypass_")
                    or clean_sub_key.startswith("override_")
                ):
                    return (
                        False,
                        "forbidden_parameter",
                        f"Forbidden override parameter {sub_key!r} is not permitted.",
                    )
                ok, vtype, reason = self._inspect_value(str(sub_key), sub_val)
                if not ok:
                    return False, vtype, reason
            return True, None, ""

        if isinstance(value, (list, tuple, set)):
            for item in value:
                ok, vtype, reason = self._inspect_value(key_name, item)
                if not ok:
                    return False, vtype, reason
            return True, None, ""

        return True, None, ""

    def validate_tool_call(
        self,
        tool_name: Any,
        tool_args: dict[str, Any] | None = None,
        *,
        allowlist: Iterable[str] | None = None,
        allowed_tools: Iterable[str] | None = None,
        raise_on_block: bool | None = None,
        tool_context: Any = None,
    ) -> HookDecision:
        """
        /**
         * Validate a proposed tool call against the allowlist and parameter security rules.
         *
         * Why: Acts as the core `PreToolUse` enforcement entrypoint. Rejects empty or
         * non-string tool names, unapproved tools, forbidden override parameters,
         * path traversal sequences, oversized payloads, and prompt injection strings
         * before any tool logic executes.
         *
         * @param tool_name Name of the tool requested by the agent.
         * @param tool_args Dictionary of tool arguments proposed by the agent.
         * @param allowlist Optional per-call allowlist override.
         * @param allowed_tools Optional alias for `allowlist`.
         * @param raise_on_block Optional override to raise `ToolAuthorizationError` on block.
         * @param tool_context Optional ADK tool execution context.
         * @return `HookDecision` indicating whether the call is allowed and why.
         */
        """
        del tool_context
        effective_raise = (
            self.raise_on_block if raise_on_block is None else bool(raise_on_block)
        )
        override_list = allowlist if allowlist is not None else allowed_tools
        effective_allowlist = (
            {str(item).strip() for item in override_list if str(item).strip()}
            if override_list is not None
            else self.allowlist
        )
        safe_args_for_log = tool_args if isinstance(tool_args, dict) else {}

        # 1. Validate tool_name is a non-empty string
        if not isinstance(tool_name, str) or not tool_name.strip():
            reason = "Tool name must be a non-empty string."
            vtype = "invalid_tool_name"
            event = self._record_audit_event(
                tool_name=str(tool_name or ""),
                allowed=False,
                reason=reason,
                violation_type=vtype,
                tool_args=safe_args_for_log,
            )
            if effective_raise:
                raise ToolAuthorizationError(
                    reason,
                    tool_name=str(tool_name or ""),
                    violation_type=vtype,
                    audit_event=event,
                )
            return HookDecision(
                allowed=False,
                tool_name=str(tool_name or ""),
                sanitized_args={},
                reason=reason,
                violation_type=vtype,
                audit_event=event,
            )

        clean_tool = tool_name.strip()

        # 2. Enforce tool allowlist
        if clean_tool not in effective_allowlist:
            reason = (
                f"Tool {clean_tool!r} is not in the approved PreToolUse allowlist "
                f"({sorted(effective_allowlist)})."
            )
            vtype = "unauthorized_tool"
            event = self._record_audit_event(
                tool_name=clean_tool,
                allowed=False,
                reason=reason,
                violation_type=vtype,
                tool_args=safe_args_for_log,
            )
            if effective_raise:
                raise ToolAuthorizationError(
                    reason,
                    tool_name=clean_tool,
                    violation_type=vtype,
                    audit_event=event,
                )
            return HookDecision(
                allowed=False,
                tool_name=clean_tool,
                sanitized_args={},
                reason=reason,
                violation_type=vtype,
                audit_event=event,
            )

        # 3. Validate tool_args type
        if tool_args is not None and not isinstance(tool_args, dict):
            reason = "Tool arguments must be provided as a dictionary."
            vtype = "invalid_tool_args"
            event = self._record_audit_event(
                tool_name=clean_tool,
                allowed=False,
                reason=reason,
                violation_type=vtype,
                tool_args={},
            )
            if effective_raise:
                raise ToolAuthorizationError(
                    reason,
                    tool_name=clean_tool,
                    violation_type=vtype,
                    audit_event=event,
                )
            return HookDecision(
                allowed=False,
                tool_name=clean_tool,
                sanitized_args={},
                reason=reason,
                violation_type=vtype,
                audit_event=event,
            )

        args_dict: dict[str, Any] = copy.deepcopy(tool_args or {})

        # 4. Check forbidden override keys and inspect argument values recursively
        for raw_key, val in args_dict.items():
            clean_key = str(raw_key).strip().lower()
            if (
                clean_key in FORBIDDEN_ARG_KEYS
                or clean_key.startswith("bypass_")
                or clean_key.startswith("override_")
            ):
                reason = f"Forbidden parameter {raw_key!r} is not permitted by PreToolUse policy."
                vtype = "forbidden_parameter"
                event = self._record_audit_event(
                    tool_name=clean_tool,
                    allowed=False,
                    reason=reason,
                    violation_type=vtype,
                    tool_args=args_dict,
                )
                if effective_raise:
                    raise ToolAuthorizationError(
                        reason,
                        tool_name=clean_tool,
                        violation_type=vtype,
                        audit_event=event,
                    )
                return HookDecision(
                    allowed=False,
                    tool_name=clean_tool,
                    sanitized_args={},
                    reason=reason,
                    violation_type=vtype,
                    audit_event=event,
                )

            ok, vtype, reason = self._inspect_value(str(raw_key), val)
            if not ok:
                event = self._record_audit_event(
                    tool_name=clean_tool,
                    allowed=False,
                    reason=reason,
                    violation_type=vtype,
                    tool_args=args_dict,
                )
                if effective_raise:
                    raise ToolAuthorizationError(
                        reason,
                        tool_name=clean_tool,
                        violation_type=vtype or "parameter_violation",
                        audit_event=event,
                    )
                return HookDecision(
                    allowed=False,
                    tool_name=clean_tool,
                    sanitized_args={},
                    reason=reason,
                    violation_type=vtype,
                    audit_event=event,
                )

        # 5. Tool call is authorized
        ok_reason = f"Tool call {clean_tool!r} authorized by PreToolUse lifecycle policy."
        event = self._record_audit_event(
            tool_name=clean_tool,
            allowed=True,
            reason=ok_reason,
            violation_type=None,
            tool_args=args_dict,
        )
        return HookDecision(
            allowed=True,
            tool_name=clean_tool,
            sanitized_args=args_dict,
            reason=ok_reason,
            violation_type=None,
            audit_event=event,
        )

    def validate(
        self,
        tool_name: Any,
        tool_args: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> HookDecision:
        """
        /**
         * Alias method delegating to `validate_tool_call`.
         *
         * Why: Supports callers invoking `hook.validate(tool_name, tool_args)`.
         *
         * @param tool_name Name of the tool to validate.
         * @param tool_args Dictionary of tool arguments.
         * @return `HookDecision` evaluation result.
         */
        """
        return self.validate_tool_call(tool_name, tool_args, **kwargs)

    def before_tool_use(
        self,
        tool_name: Any,
        tool_args: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> HookDecision:
        """
        /**
         * Lifecycle callback alias delegating to `validate_tool_call`.
         *
         * Why: Matches ADK's `before_tool_use` hook naming convention.
         *
         * @param tool_name Name of the tool being invoked.
         * @param tool_args Dictionary of tool arguments.
         * @return `HookDecision` evaluation result.
         */
        """
        return self.validate_tool_call(tool_name, tool_args, **kwargs)

    def check(
        self,
        tool_name: Any,
        tool_args: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> HookDecision:
        """
        /**
         * Alias method delegating to `validate_tool_call`.
         *
         * Why: Supports guard-style `hook.check(tool_name, tool_args)` invocations.
         *
         * @param tool_name Name of the tool being checked.
         * @param tool_args Dictionary of tool arguments.
         * @return `HookDecision` evaluation result.
         */
        """
        return self.validate_tool_call(tool_name, tool_args, **kwargs)

    def __call__(
        self,
        tool_name: Any,
        tool_args: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> HookDecision:
        """
        /**
         * Make `PreToolUseHook` instances directly callable as ADK `before_tool_callback`s.
         *
         * Why: Allows passing `PreToolUseHook()` directly to `Agent(before_tool_callback=...)`.
         *
         * @param tool_name Name of the tool being invoked.
         * @param tool_args Dictionary of tool arguments.
         * @return `HookDecision` evaluation result.
         */
        """
        return self.validate_tool_call(tool_name, tool_args, **kwargs)


PreToolUseGuard = PreToolUseHook
ToolLifecycleGuard = PreToolUseHook

_DEFAULT_HOOK = PreToolUseHook()


def validate_tool_call(
    tool_name: Any,
    tool_args: dict[str, Any] | None = None,
    *,
    allowlist: Iterable[str] | None = None,
    allowed_tools: Iterable[str] | None = None,
    raise_on_block: bool = False,
    tool_context: Any = None,
) -> HookDecision:
    """
    /**
     * Module-level helper that validates a tool invocation using the default `PreToolUseHook`.
     *
     * Why: Provides a stateless functional interface for callers and ADK agent hooks
     * while recording events in the module-level `AUDIT_LOG`.
     *
     * @param tool_name Name of the tool requested by the agent.
     * @param tool_args Dictionary of tool arguments.
     * @param allowlist Optional tool allowlist override.
     * @param allowed_tools Optional alias for `allowlist`.
     * @param raise_on_block Whether to raise `ToolAuthorizationError` when blocked.
     * @param tool_context Optional ADK tool context.
     * @return `HookDecision` indicating whether the tool call is permitted.
     */
    """
    return _DEFAULT_HOOK.validate_tool_call(
        tool_name,
        tool_args,
        allowlist=allowlist,
        allowed_tools=allowed_tools,
        raise_on_block=raise_on_block,
        tool_context=tool_context,
    )


def before_tool_callback(
    tool_name: Any,
    tool_args: dict[str, Any] | None = None,
    **kwargs: Any,
) -> HookDecision:
    """
    /**
     * ADK `before_tool_callback` entrypoint delegating to `validate_tool_call`.
     *
     * Why: Matches the `Agent(before_tool_callback=...)` parameter name in ADK.
     *
     * @param tool_name Name of the tool being called.
     * @param tool_args Dictionary of tool arguments.
     * @return `HookDecision` evaluation result.
     */
    """
    return validate_tool_call(tool_name, tool_args, **kwargs)


def validate_tool_use(
    tool_name: Any,
    tool_args: dict[str, Any] | None = None,
    **kwargs: Any,
) -> HookDecision:
    """
    /**
     * Alias function for `validate_tool_call`.
     *
     * Why: Supports callers importing `validate_tool_use` from Step 3a.
     *
     * @param tool_name Name of the tool being called.
     * @param tool_args Dictionary of tool arguments.
     * @return `HookDecision` evaluation result.
     */
    """
    return validate_tool_call(tool_name, tool_args, **kwargs)


def check_tool_call(
    tool_name: Any,
    tool_args: dict[str, Any] | None = None,
    **kwargs: Any,
) -> HookDecision:
    """
    /**
     * Alias function for `validate_tool_call`.
     *
     * Why: Supports callers importing `check_tool_call` from Step 3a.
     *
     * @param tool_name Name of the tool being called.
     * @param tool_args Dictionary of tool arguments.
     * @return `HookDecision` evaluation result.
     */
    """
    return validate_tool_call(tool_name, tool_args, **kwargs)


__all__ = [
    "ALLOWED_TOOLS",
    "AUDIT_LOG",
    "DEFAULT_ALLOWLIST",
    "DEFAULT_TOOL_ALLOWLIST",
    "FORBIDDEN_ARG_KEYS",
    "HookDecision",
    "MAX_ARG_LENGTH",
    "PATH_SENSITIVE_ARG_KEYS",
    "PROMPT_INJECTION_PATTERNS",
    "PreToolUseGuard",
    "PreToolUseHook",
    "ToolAuthorizationError",
    "ToolLifecycleGuard",
    "before_tool_callback",
    "check_tool_call",
    "validate_tool_call",
    "validate_tool_use",
]
