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
 * @file memory_bank.py
 * @description Session persistence and long-term semantic memory service for
 *   Gemini Enterprise Agent Platform Memory Bank.
 *
 * Why: Multi-agent campaign workflows need both short-term session state (to resume
 * paused Human-in-the-Loop approval gates across HTTP/A2A requests) and long-term
 * namespace memories (to recall brand preferences and prior campaign pitches).
 * Using dependency injection with defensive deep copies lets unit and E2E tests
 * verify multi-turn persistence offline without mutating shared references.
 */
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
import time
from typing import Any


@dataclass
class MemoryEntry:
    """
    /**
     * Structured long-term memory entry stored in `MemoryBankService`.
     *
     * Why: Captures namespace, key, arbitrary JSON-serializable payload, and creation
     * timestamp so retrieval queries can filter and sort memories deterministically.
     *
     * @param namespace Logical partition (e.g., `"campaigns"` or `"brand_guidelines"`).
     * @param key Unique identifier within the namespace.
     * @param value Stored memory payload.
     * @param timestamp Unix epoch timestamp when the memory was persisted.
     */
    """

    namespace: str
    key: str
    value: Any
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        """
        /**
         * Convert this memory entry into a defensive dictionary representation.
         *
         * Why: Returns a deep copy of `value` so callers inspecting retrieved memories
         * cannot accidentally mutate internal Memory Bank state.
         *
         * @return Dictionary with `namespace`, `key`, `value`, and `timestamp`.
         */
        """
        return {
            "namespace": self.namespace,
            "key": self.key,
            "value": copy.deepcopy(self.value),
            "timestamp": self.timestamp,
        }


class MemoryBankService:
    """
    /**
     * Injectable session and long-term memory provider compatible with Agent Platform
     * Memory Bank.
     *
     * Why: Decouples agent workflow state management from live cloud storage so
     * sessions, HITL pause/resume states, and campaign memories work identically
     * in offline unit tests and Cloud Run deployments.
     */
    """

    def __init__(
        self,
        memory_bank_id: str = "pitch-generator-memory",
        client: Any = None,
    ) -> None:
        """
        /**
         * Initialize the Memory Bank service.
         *
         * Why: Accepts an optional external `client` for live Agent Platform Memory Bank
         * forwarding while maintaining deterministic in-memory storage for offline runs.
         *
         * @param memory_bank_id Identifier for the target Memory Bank store.
         * @param client Optional external Memory Bank SDK client for DI.
         */
        """
        if not memory_bank_id or not memory_bank_id.strip():
            raise ValueError("memory_bank_id must not be empty")
        self.memory_bank_id = memory_bank_id.strip()
        self.client = client
        self._sessions: dict[str, dict[str, Any]] = {}
        self._memories: dict[str, dict[str, MemoryEntry]] = {}

    def save_session(self, session_id: str, state: dict[str, Any]) -> None:
        """
        /**
         * Persist a session state dictionary under `session_id`.
         *
         * Why: Deep-copies `state` before storing so subsequent in-place modifications
         * by caller code do not corrupt the saved checkpoint.
         *
         * @param session_id Non-empty session identifier.
         * @param state Dictionary of workflow session state to persist.
         * @return None.
         */
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must not be empty")
        if not isinstance(state, dict):
            raise ValueError("state must be a dictionary")
        clean_id = session_id.strip()
        snapshot = copy.deepcopy(state)
        self._sessions[clean_id] = snapshot
        if self.client is not None and hasattr(self.client, "save_session"):
            self.client.save_session(clean_id, copy.deepcopy(snapshot))

    def load_session(self, session_id: str) -> dict[str, Any]:
        """
        /**
         * Load the persisted state dictionary for `session_id`.
         *
         * Why: Returns a deep copy of the stored session (or `{}` if not yet created)
         * so workflow resume logic can safely mutate the returned dictionary.
         *
         * @param session_id Non-empty session identifier to look up.
         * @return Deep-copied session state dictionary, or `{}` if unknown.
         */
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must not be empty")
        clean_id = session_id.strip()
        if clean_id in self._sessions:
            return copy.deepcopy(self._sessions[clean_id])
        if self.client is not None and hasattr(self.client, "load_session"):
            external = self.client.load_session(clean_id)
            if isinstance(external, dict):
                return copy.deepcopy(external)
        return {}

    def store_memory(self, namespace: str, key: str, value: Any) -> None:
        """
        /**
         * Store a long-term memory entry under `(namespace, key)`.
         *
         * Why: Organizes long-term agent memories by namespace (such as `"campaigns"`,
         * `"brand_guidelines"`, or `"user_preferences"`) to prevent key collisions.
         *
         * @param namespace Non-empty logical namespace string.
         * @param key Non-empty memory key string.
         * @param value Arbitrary JSON-serializable memory value.
         * @return None.
         */
        """
        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError("namespace must not be empty")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("key must not be empty")
        clean_ns = namespace.strip()
        clean_key = key.strip()
        entry = MemoryEntry(
            namespace=clean_ns,
            key=clean_key,
            value=copy.deepcopy(value),
            timestamp=time.time(),
        )
        ns_bucket = self._memories.setdefault(clean_ns, {})
        ns_bucket[clean_key] = entry
        if self.client is not None and hasattr(self.client, "store_memory"):
            self.client.store_memory(clean_ns, clean_key, copy.deepcopy(value))

    def retrieve_memories(self, namespace: str, query: str = "") -> list[dict[str, Any]]:
        """
        /**
         * Retrieve long-term memories from `namespace`, optionally filtered by `query`.
         *
         * Why: Supports case-insensitive substring matching across both memory keys
         * and serialized values so agents can recall relevant campaign history offline.
         *
         * @param namespace Logical namespace to search.
         * @param query Optional case-insensitive search substring.
         * @return List of matching memory entry dictionaries ordered by insertion.
         */
        """
        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError("namespace must not be empty")
        clean_ns = namespace.strip()
        ns_bucket = self._memories.get(clean_ns, {})
        needle = (query or "").strip().lower()
        results: list[dict[str, Any]] = []
        for entry in ns_bucket.values():
            if needle:
                haystack = f"{entry.key} {entry.value}".lower()
                if needle not in haystack:
                    continue
            results.append(entry.to_dict())
        return results

    def list_sessions(self) -> list[str]:
        """
        /**
         * Return a sorted list of all active session IDs stored in the Memory Bank.
         *
         * Why: Useful for administrative inspection and test assertions on session lifecycle.
         *
         * @return Sorted list of session ID strings.
         */
        """
        return sorted(self._sessions.keys())

    def clear(self) -> None:
        """
        /**
         * Clear all stored sessions and long-term memories.
         *
         * Why: Enables fast state reset between test cases when reusing a service instance.
         *
         * @return None.
         */
        """
        self._sessions.clear()
        self._memories.clear()
