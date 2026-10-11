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
 * @file step_3b_pii_scrubbing.py
 * @description Module 3 Step 3b reference solution implementing deterministic
 *   Sensitive PII and Secret Data Scrubbing across raw strings, nested dicts/lists,
 *   Memory Bank payloads, and telemetry logs.
 *
 * Why: Campaign briefs submitted by users often contain accidental PII (emails,
 * phone numbers, SSNs, credit cards) or leaked credentials (Bearer tokens, `sk-...`,
 * `AIza...` keys). Scrubbing these patterns before LLM invocation, Memory Bank
 * persistence, and BigQuery logging prevents sensitive data leakage while
 * preserving benign product numbers, dates, and metrics (`docs/outline.md` §5.2).
 */
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any, Iterator

REDACTED_EMAIL: str = "[REDACTED_EMAIL]"
REDACTED_PHONE: str = "[REDACTED_PHONE]"
REDACTED_SSN: str = "[REDACTED_SSN]"
REDACTED_CC: str = "[REDACTED_CC]"
REDACTED_SECRET: str = "[REDACTED_SECRET]"

# Ordered from most specific (secrets, emails, 16-digit credit cards) to
# shorter numeric patterns (SSNs, phone numbers) so 16-digit card numbers or
# high-entropy tokens are never partially matched by shorter patterns.
PII_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "secret",
        REDACTED_SECRET,
        re.compile(
            r"(?:\bBearer\s+[A-Za-z0-9._\-]+|\bsk-(?:live-|test-|proj-)?[A-Za-z0-9_\-]{12,}|\bAIza[A-Za-z0-9_\-]{16,}|\bghp_[A-Za-z0-9]{20,}|\bxox[baprs]-[A-Za-z0-9\-]{10,})"
        ),
    ),
    (
        "email",
        REDACTED_EMAIL,
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "credit_card",
        REDACTED_CC,
        re.compile(r"\b(?:\d{4}[-\s]){3}\d{4}\b|\b\d{16}\b"),
    ),
    (
        "ssn",
        REDACTED_SSN,
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    ),
    (
        "phone",
        REDACTED_PHONE,
        re.compile(
            r"(?:(?:\+\d{1,2}[-\s.]?)?(?:\(\d{3}\)|\b\d{3})[-\s.]\d{3}[-\s.]\d{4})\b"
        ),
    ),
)


@dataclass
class ScrubResult:
    """
    /**
     * Structured result container returned by `PIIScrubber` methods.
     *
     * Why: Callers across the application and test suite consume PII scrubbing
     * results in multiple ways: tuple unpacking (`scrubbed, count = ...`),
     * attribute/property extraction (`res.scrubbed`, `res.redaction_count`,
     * `res.count`), substring checks (`"[REDACTED_EMAIL]" in res`), dictionary
     * indexing (`res["contact"]`), or direct string formatting (`str(res)`).
     * Encapsulating both the scrubbed payload and integer redaction count avoids
     * colliding with Python's built-in `str.count` / `list.count` methods.
     */
    """

    scrubbed: Any
    redaction_count: int = 0
    counts_by_type: dict[str, int] = field(default_factory=dict)

    @property
    def sanitized(self) -> Any:
        """
        /**
         * Alias property returning the scrubbed value.
         *
         * Why: Supports callers inspecting `result.sanitized`.
         *
         * @return Scrubbed string, dict, list, or primitive value.
         */
        """
        return self.scrubbed

    @property
    def text(self) -> str:
        """
        /**
         * Return the scrubbed value formatted as a string.
         *
         * Why: Supports callers reading `result.text` on string or structured outputs.
         *
         * @return Scrubbed string or JSON-serialized representation.
         */
        """
        if isinstance(self.scrubbed, str):
            return self.scrubbed
        if self.scrubbed is None:
            return ""
        return json.dumps(self.scrubbed, default=str)

    @property
    def data(self) -> Any:
        """
        /**
         * Alias property returning the scrubbed value.
         *
         * Why: Supports callers inspecting `result.data`.
         *
         * @return Scrubbed payload.
         */
        """
        return self.scrubbed

    @property
    def payload(self) -> Any:
        """
        /**
         * Alias property returning the scrubbed value.
         *
         * Why: Supports callers inspecting `result.payload`.
         *
         * @return Scrubbed payload.
         */
        """
        return self.scrubbed

    @property
    def count(self) -> int:
        """
        /**
         * Return the total number of PII/secret tokens redacted.
         *
         * Why: Provides an integer property `.count` (rather than the bound method
         * `str.count`) so `int(result.count)` succeeds in telemetry and E2E checks.
         *
         * @return Non-negative integer count of redactions performed.
         */
        """
        return self.redaction_count

    @property
    def total_redactions(self) -> int:
        """
        /**
         * Alias property returning `self.redaction_count`.
         *
         * Why: Supports callers inspecting `result.total_redactions`.
         *
         * @return Total number of redactions performed.
         */
        """
        return self.redaction_count

    def to_dict(self) -> dict[str, Any]:
        """
        /**
         * Serialize the `ScrubResult` into a plain dictionary.
         *
         * Why: Enables structured telemetry serialization and `extract_field` lookup.
         *
         * @return Dictionary with `scrubbed`, `redaction_count`, and `counts_by_type`.
         */
        """
        return {
            "scrubbed": self.scrubbed,
            "sanitized": self.scrubbed,
            "redaction_count": self.redaction_count,
            "count": self.redaction_count,
            "total_redactions": self.redaction_count,
            "counts_by_type": dict(self.counts_by_type),
        }

    def __iter__(self) -> Iterator[Any]:
        """
        /**
         * Yield `(self.scrubbed, self.redaction_count)` for 2-tuple unpacking.
         *
         * Why: Allows callers to write `scrubbed_val, count = scrubber.scrub_text(s)`.
         *
         * @return Iterator yielding the scrubbed payload followed by `redaction_count`.
         */
        """
        yield self.scrubbed
        yield self.redaction_count

    def __contains__(self, item: Any) -> bool:
        """
        /**
         * Check whether `item` is contained in `self.scrubbed`.
         *
         * Why: Allows direct assertions like `assert "[REDACTED_EMAIL]" in result`.
         *
         * @param item Substring or key to check.
         * @return `True` if `item` is in `self.scrubbed`.
         */
        """
        if self.scrubbed is None:
            return False
        if isinstance(self.scrubbed, (str, dict, list, tuple, set)):
            return item in self.scrubbed
        return str(item) in str(self.scrubbed)

    def __eq__(self, other: object) -> bool:
        """
        /**
         * Compare `ScrubResult` against another `ScrubResult` or directly against a
         * raw scrubbed value (`str`, `dict`, `list`, `None`).
         *
         * Why: Allows callers that compare `scrubber.scrub_text("") == ""` or
         * `scrubber.scrub_payload({}) == {}` to succeed seamlessly.
         *
         * @param other Object to compare with.
         * @return `True` if equal.
         */
        """
        if isinstance(other, ScrubResult):
            return (
                self.scrubbed == other.scrubbed
                and self.redaction_count == other.redaction_count
            )
        return bool(self.scrubbed == other)

    def __getitem__(self, key: Any) -> Any:
        """
        /**
         * Delegate indexing (`result[key]`) to `self.scrubbed` or the result fields.
         *
         * Why: Allows indexing into a scrubbed dictionary/list directly or reading
         * `"scrubbed"` / `"redaction_count"` keys.
         *
         * @param key Key or index to look up.
         * @return Value from `self.scrubbed` or serialized result dictionary.
         */
        """
        if isinstance(self.scrubbed, dict) and key in self.scrubbed:
            return self.scrubbed[key]
        if isinstance(self.scrubbed, (list, tuple, str)) and isinstance(
            key, (int, slice)
        ):
            return self.scrubbed[key]
        res_dict = self.to_dict()
        if isinstance(key, str) and key in res_dict:
            return res_dict[key]
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        """
        /**
         * Support `.get(key, default)` lookup on scrubbed dictionaries or result metadata.
         *
         * Why: Ensures compatibility with dictionary-based consumers.
         *
         * @param key Key name to look up.
         * @param default Fallback value if `key` is not found.
         * @return Value or `default`.
         */
        """
        if isinstance(self.scrubbed, dict) and key in self.scrubbed:
            return self.scrubbed[key]
        return self.to_dict().get(key, default)

    def __len__(self) -> int:
        """
        /**
         * Return the length of `self.scrubbed` when it is a sized container or string.
         *
         * Why: Allows `len(result)` checks on scrubbed strings, dicts, and lists.
         *
         * @return Length of `self.scrubbed`, or `0` if `None`.
         */
        """
        if self.scrubbed is None:
            return 0
        if isinstance(self.scrubbed, (str, dict, list, tuple, set)):
            return len(self.scrubbed)
        return len(str(self.scrubbed))

    def __str__(self) -> str:
        """
        /**
         * Return the string representation of `self.scrubbed`.
         *
         * Why: Ensures `str(result)` yields the clean redacted text.
         *
         * @return String form of `self.scrubbed`.
         */
        """
        if self.scrubbed is None:
            return ""
        if isinstance(self.scrubbed, str):
            return self.scrubbed
        return json.dumps(self.scrubbed, default=str)


class PIIScrubber:
    """
    /**
     * Deterministic PII and secret scrubber for strings and nested data structures.
     *
     * Why: Encapsulates ordered regex rules for emails, phone numbers, SSNs,
     * credit card numbers, and API keys/Bearer tokens, ensuring idempotent
     * redaction and zero in-place mutation of caller-owned dictionaries or lists
     * (`docs/outline.md` §5.2).
     */
    """

    def __init__(
        self,
        patterns: tuple[tuple[str, str, re.Pattern[str]], ...] = PII_PATTERNS,
    ) -> None:
        """
        /**
         * Initialize the `PIIScrubber` with ordered redaction patterns.
         *
         * Why: Allows dependency injection of custom regex patterns in tests while
         * defaulting to the canonical `PII_PATTERNS` suite.
         *
         * @param patterns Tuple of `(category_name, placeholder, compiled_regex)` triples.
         */
        """
        self.patterns = patterns

    def scrub_text(self, text: str | None) -> ScrubResult:
        """
        /**
         * Redact all PII and secret tokens from a string without altering benign numbers.
         *
         * Why: Replaces sensitive tokens with typed placeholders (`[REDACTED_EMAIL]`,
         * `[REDACTED_PHONE]`, `[REDACTED_SSN]`, `[REDACTED_CC]`, `[REDACTED_SECRET]`)
         * while leaving already-redacted placeholders, dates (`2026-10-15`), and
         * product metrics (`350 lumen`, `24-hour`, `45%`) untouched (`count == 0`).
         *
         * @param text Input string (or `None`) to scrub.
         * @return `ScrubResult` containing the redacted text and redaction count.
         */
        """
        if text is None or not isinstance(text, str) or not text:
            return ScrubResult(scrubbed=text, redaction_count=0, counts_by_type={})

        current = text
        total_count = 0
        counts_by_type: dict[str, int] = {}

        for category, placeholder, pattern in self.patterns:
            current, replacements = pattern.subn(placeholder, current)
            if replacements > 0:
                total_count += replacements
                counts_by_type[category] = (
                    counts_by_type.get(category, 0) + replacements
                )

        return ScrubResult(
            scrubbed=current,
            redaction_count=total_count,
            counts_by_type=counts_by_type,
        )

    def scrub_payload(self, payload: Any) -> ScrubResult:
        """
        /**
         * Recursively scrub PII and secrets across strings, dicts, lists, and tuples
         * without mutating the caller's input structure in-place.
         *
         * Why: Session states, Memory Bank entries, and telemetry payloads are deeply
         * nested dictionaries and lists containing mixed types (`str`, `int`, `float`,
         * `bool`, `None`). Building a new structure preserves primitive types and
         * caller immutability while aggregating total redactions across all leaves.
         *
         * @param payload Arbitrary string, dictionary, list, tuple, or primitive value.
         * @return `ScrubResult` with the deep-copied scrubbed structure and total count.
         */
        """
        if payload is None or isinstance(payload, (bool, int, float)):
            return ScrubResult(scrubbed=payload, redaction_count=0, counts_by_type={})

        if isinstance(payload, str):
            return self.scrub_text(payload)

        if isinstance(payload, dict):
            new_dict: dict[Any, Any] = {}
            total_count = 0
            merged_counts: dict[str, int] = {}
            for key, val in payload.items():
                if isinstance(key, str):
                    key_res = self.scrub_text(key)
                    clean_key = key_res.scrubbed
                    total_count += key_res.redaction_count
                    for cat, c in key_res.counts_by_type.items():
                        merged_counts[cat] = merged_counts.get(cat, 0) + c
                else:
                    clean_key = key

                val_res = self.scrub_payload(val)
                new_dict[clean_key] = val_res.scrubbed
                total_count += val_res.redaction_count
                for cat, c in val_res.counts_by_type.items():
                    merged_counts[cat] = merged_counts.get(cat, 0) + c

            return ScrubResult(
                scrubbed=new_dict,
                redaction_count=total_count,
                counts_by_type=merged_counts,
            )

        if isinstance(payload, (list, tuple)):
            new_items: list[Any] = []
            total_count = 0
            merged_counts = {}
            for item in payload:
                item_res = self.scrub_payload(item)
                new_items.append(item_res.scrubbed)
                total_count += item_res.redaction_count
                for cat, c in item_res.counts_by_type.items():
                    merged_counts[cat] = merged_counts.get(cat, 0) + c

            out_seq: Any = tuple(new_items) if isinstance(payload, tuple) else new_items
            return ScrubResult(
                scrubbed=out_seq,
                redaction_count=total_count,
                counts_by_type=merged_counts,
            )

        return ScrubResult(scrubbed=payload, redaction_count=0, counts_by_type={})

    def scrub_dict(self, payload: Any) -> ScrubResult:
        """
        /**
         * Alias method delegating to `scrub_payload` for dictionary inputs.
         *
         * Why: Supports callers invoking `scrubber.scrub_dict(data)`.
         *
         * @param payload Dictionary or structured payload to scrub.
         * @return `ScrubResult` containing the scrubbed dictionary and redaction count.
         */
        """
        return self.scrub_payload(payload)

    def scrub(self, payload: Any) -> ScrubResult:
        """
        /**
         * General-purpose alias delegating to `scrub_payload`.
         *
         * Why: Supports callers invoking `scrubber.scrub(payload)` on either strings
         * or nested data structures.
         *
         * @param payload String or structured payload to scrub.
         * @return `ScrubResult` containing the scrubbed value and redaction count.
         */
        """
        return self.scrub_payload(payload)

    def sanitize(self, payload: Any) -> ScrubResult:
        """
        /**
         * Alias method delegating to `scrub_payload`.
         *
         * Why: Supports callers invoking `scrubber.sanitize(payload)`.
         *
         * @param payload String or structured payload to sanitize.
         * @return `ScrubResult` containing the sanitized value and redaction count.
         */
        """
        return self.scrub_payload(payload)

    def __call__(self, payload: Any) -> ScrubResult:
        """
        /**
         * Make `PIIScrubber` instances directly callable as pipeline transforms.
         *
         * Why: Enables passing `PIIScrubber()` directly as a callback function.
         *
         * @param payload String or structured payload to scrub.
         * @return `ScrubResult` containing the scrubbed value and redaction count.
         */
        """
        return self.scrub_payload(payload)


_DEFAULT_SCRUBBER = PIIScrubber()


def scrub_text(text: str | None) -> ScrubResult:
    """
    /**
     * Module-level helper that scrubs PII and secrets from a string.
     *
     * Why: Provides a stateless functional entrypoint returning a `ScrubResult`.
     *
     * @param text Input string (or `None`) to scrub.
     * @return `ScrubResult` with `.scrubbed` and `.redaction_count`.
     */
    """
    return _DEFAULT_SCRUBBER.scrub_text(text)


def scrub_payload(payload: Any) -> ScrubResult:
    """
    /**
     * Module-level helper that recursively scrubs PII and secrets from any payload.
     *
     * Why: Provides a stateless functional entrypoint for dicts, lists, and strings.
     *
     * @param payload Arbitrary string, dict, list, or primitive value.
     * @return `ScrubResult` with `.scrubbed` and `.redaction_count`.
     */
    """
    return _DEFAULT_SCRUBBER.scrub_payload(payload)


def scrub_dict(payload: Any) -> ScrubResult:
    """
    /**
     * Module-level alias for `scrub_payload` when scrubbing dictionaries.
     *
     * Why: Matches callers importing `scrub_dict` from Step 3b.
     *
     * @param payload Dictionary or nested structure to scrub.
     * @return `ScrubResult` with `.scrubbed` and `.redaction_count`.
     */
    """
    return _DEFAULT_SCRUBBER.scrub_payload(payload)


def scrub_pii(payload: Any) -> ScrubResult:
    """
    /**
     * Canonical module-level function that scrubs PII and secrets from `payload`.
     *
     * Why: Primary functional entrypoint resolved by E2E and unit test suites.
     *
     * @param payload String or structured payload to scrub.
     * @return `ScrubResult` with `.scrubbed` and `.redaction_count`.
     */
    """
    return _DEFAULT_SCRUBBER.scrub_payload(payload)


def sanitize_pii(payload: Any) -> ScrubResult:
    """
    /**
     * Alias module-level function delegating to `scrub_payload`.
     *
     * Why: Supports callers importing `sanitize_pii` from Step 3b.
     *
     * @param payload String or structured payload to sanitize.
     * @return `ScrubResult` with `.scrubbed` and `.redaction_count`.
     */
    """
    return _DEFAULT_SCRUBBER.scrub_payload(payload)


def scrub_sensitive_data(payload: Any) -> Any:
    """
    /**
     * Convenience function returning the unwrapped scrubbed payload directly.
     *
     * Why: Allows callers that want the raw sanitized `str` or `dict` without
     * unpacking `ScrubResult` to sanitize values inline.
     *
     * @param payload Arbitrary string, dict, list, or primitive value.
     * @return The sanitized value of the same type as `payload`.
     */
    """
    return _DEFAULT_SCRUBBER.scrub_payload(payload).scrubbed


__all__ = [
    "PII_PATTERNS",
    "PIIScrubber",
    "REDACTED_CC",
    "REDACTED_EMAIL",
    "REDACTED_PHONE",
    "REDACTED_SECRET",
    "REDACTED_SSN",
    "ScrubResult",
    "sanitize_pii",
    "scrub_dict",
    "scrub_payload",
    "scrub_pii",
    "scrub_sensitive_data",
    "scrub_text",
]
