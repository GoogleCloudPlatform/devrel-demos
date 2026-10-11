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
 * @file runtime_clients.py
 * @description Runtime LLM client adapters (`EnterpriseGenAILLMClient`,
 *   `DeterministicMockLLMClient`) and Cloud Storage artifact persistence
 *   (`InMemoryArtifactService`, `GcsArtifactService`, `get_artifact_service`).
 *
 * Why: Separating low-level Vertex AI rate-limiting/caching and Cloud Storage
 * binary artifact plumbing into a focused runtime module keeps
 * `pitch_generator/app_utils/services.py` concise and centered on
 * `BigQueryAnalyticsService`, `ServiceContainer`, and the Module 2 & 3 lab steps.
 */
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import os
import random
import re
import struct
import sys
import threading
import time
from typing import Any, Protocol, runtime_checkable
import zlib

from pitch_generator.config import (
    PitchConfig,
    get_config,
    normalize_bucket_name,
)


def _build_house_brand_png(width: int = 320, height: int = 180) -> bytes:
    """
    /**
     * Build a deterministic 16:9 house-brand PNG (deep indigo/slate with warm amber light)
     * using only the Python standard library (`struct` and `zlib`).
     *
     * Why: Ensures offline fallback key visuals render as a clean 16:9 brand-compliant
     * studio visual in the browser `<img>` preview while maintaining valid PNG chunks.
     *
     * @param width Image width in pixels (default `320`).
     * @param height Image height in pixels (default `180`).
     * @return Raw PNG image bytes.
     */
    """

    def _chunk(chunk_type: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", crc)

    raw_rows = bytearray()
    cx, cy = int(width * 0.34), int(height * 0.54)
    radius_sq = (min(width, height) * 0.24) ** 2
    for y in range(height):
        raw_rows.append(0)  # Filter type 0 (None)
        yf = y / max(height - 1, 1)
        for x in range(width):
            xf = x / max(width - 1, 1)
            # Base deep indigo (#1e1b4b) to weathered slate (#334155) gradient
            r = int(30 + 21 * xf + 10 * yf)
            g = int(27 + 38 * xf + 16 * yf)
            b = int(75 + 10 * xf + 18 * yf)
            # Off-center hero subject with warm amber (#f59e0b) raking light
            dx, dy = x - cx, y - cy
            dist_sq = dx * dx + dy * dy
            if dist_sq <= radius_sq:
                edge = 1.0 - (dist_sq / radius_sq)
                r = min(255, int(r + 215 * edge))
                g = min(255, int(g + 130 * edge))
                b = max(18, int(b - 45 * edge))
            elif y > cy and (x - cx) > 0 and abs((y - cy) - 0.32 * (x - cx)) < 14:
                # Long raking shadow across slate ground
                r = max(12, r - 14)
                g = max(14, g - 14)
                b = max(32, b - 18)
            raw_rows.extend((r, g, b))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw_rows), level=6)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", idat)
        + _chunk(b"IEND", b"")
    )


MINIMAL_PNG_BYTES: bytes = _build_house_brand_png()


@runtime_checkable
class LLMClientProtocol(Protocol):
    """
    /**
     * Protocol defining the text and image generation contract for agent models.
     *
     * Why: Decouples agent nodes from `google-genai` SDK internals so tests can
     * inject deterministic mocks or hybrid model routers without network calls.
     */
    """

    def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: str = "",
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """
        /**
         * Generate text completion for `prompt` under `system_instruction`.
         *
         * Why: Standardizes synchronous text generation across Flash, Pro, and local models.
         *
         * @param prompt User or upstream agent prompt string.
         * @param system_instruction System role instruction guiding agent behavior.
         * @param model Optional model identifier override.
         * @param temperature Sampling temperature.
         * @return Generated text response.
         */
        """
        ...

    def generate_image(
        self,
        prompt: str,
        *,
        model: str | None = None,
    ) -> tuple[bytes, str]:
        """
        /**
         * Generate a binary key visual image from `prompt`.
         *
         * Why: Returns raw `(image_bytes, mime_type)` so callers can persist the artifact
         * to `InMemoryArtifactService` or `GcsArtifactService` and attach it to A2A events.
         *
         * @param prompt Visual direction prompt describing the key visual.
         * @param model Optional image generation model override.
         * @return Tuple of `(png_bytes, mime_type)`.
         */
        """
        ...


class DeterministicMockLLMClient:
    """
    /**
     * Offline-safe implementation of `LLMClientProtocol` producing brand-aligned outputs.
     *
     * Why: Enables deterministic testing of Creative Director concepts, Copywriter
     * <25-word social captions, Brand Strategist reviews, and Visual Director house-style
     * key visuals without requiring live Gemini Enterprise Agent Platform quota.
     */
    """

    def __init__(self, config: PitchConfig | None = None) -> None:
        """
        /**
         * Initialize the deterministic mock LLM client.
         *
         * Why: Records every call in `self.calls` so tests can assert model selection,
         * prompt formatting, and system instructions.
         *
         * @param config Optional `PitchConfig` providing default model identifiers.
         */
        """
        self.config = config or get_config()
        self.calls: list[dict[str, Any]] = []

    def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: str = "",
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """
        /**
         * Produce a deterministic role-specific response based on instruction and prompt.
         *
         * Why: Inspects the role (`Copywriter`, `Visual Director`, `Brand Strategist`,
         * or `Creative Director`) so downstream assertions on word limits (<25 words)
         * and house brand guidelines (indigo/slate palette, warm amber/terracotta accent,
         * low raking light, off-center negative space, single photographic subject) pass
         * deterministically.
         *
         * @param prompt Input campaign brief or upstream concept.
         * @param system_instruction Role instruction for the active specialist agent.
         * @param model Optional model identifier.
         * @param temperature Sampling temperature.
         * @return Role-appropriate generated text.
         */
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must not be empty")

        clean_prompt = prompt.strip()
        resolved_model = model or self.config.flash_model
        self.calls.append(
            {
                "type": "text",
                "prompt": clean_prompt,
                "system_instruction": system_instruction,
                "model": resolved_model,
                "temperature": temperature,
            }
        )

        combined = f"{system_instruction}\n{clean_prompt}".lower()
        topic = self._extract_topic_summary(clean_prompt)

        if "copywriter" in combined or "social caption" in combined or "under 25 words" in combined:
            caption = (
                f"Discover {topic}: precision-crafted performance built for everyday momentum. "
                f"Step into effortless flow today. #NextGenDesign"
            )
            words = caption.split()
            if len(words) > 22:
                caption = " ".join(words[:22])
            return caption

        if "visual director" in combined or "art direction" in combined or "key visual" in combined:
            return (
                f"Art Direction for {topic}: A single realistic photographic hero subject "
                f"captured with shallow depth of field, positioned at the off-center third "
                f"with generous empty negative space across a clean background. Color palette "
                f"anchored in deep indigo and slate tones with one warm amber and terracotta "
                f"accent. Illuminated by a single low raking light source at golden hour "
                f"casting long directional shadows."
            )

        if "brand strategist" in combined or "brand alignment" in combined:
            return (
                f"Brand Strategy for {topic}: Position the campaign around quiet confidence "
                f"and tactile craftsmanship, pairing our signature deep indigo and slate "
                f"visual identity with a warm amber accent."
            )

        return (
            f"Concept Line: Momentum Reimagined for {topic}.\n"
            f"Rationale: Elevates {topic} into a human-centered story of reliability, "
            f"contrasting everyday friction with calm, purposeful engineering."
        )

    def generate_image(
        self,
        prompt: str,
        *,
        model: str | None = None,
    ) -> tuple[bytes, str]:
        """
        /**
         * Generate a deterministic valid PNG byte payload for key visual requests.
         *
         * Why: Returns `MINIMAL_PNG_BYTES` with `"image/png"` MIME type so binary file
         * writers (`call_agent.py --save-image`), `GcsArtifactService`, and A2A event
         * interceptors handle real PNG binary headers offline.
         *
         * @param prompt Visual prompt describing the key visual to render.
         * @param model Optional image model override.
         * @return Tuple of `(MINIMAL_PNG_BYTES, "image/png")`.
         */
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must not be empty")
        resolved_model = model or self.config.image_model
        self.calls.append(
            {
                "type": "image",
                "prompt": prompt.strip(),
                "model": resolved_model,
            }
        )
        return (MINIMAL_PNG_BYTES, "image/png")

    def _extract_topic_summary(self, text: str) -> str:
        """
        /**
         * Extract a concise 2-to-5 word topic phrase from a potentially multi-line prompt.
         *
         * Why: Keeps generated Copywriter captions strictly under 25 words even when the
         * input prompt includes lengthy upstream concept lines.
         *
         * @param text Raw prompt text.
         * @return Concise topic string (at most 5 words).
         */
        """
        first_line = text.splitlines()[0].strip()
        for prefix in ("concept line:", "brief:", "campaign brief:", "topic:"):
            if first_line.lower().startswith(prefix):
                first_line = first_line[len(prefix) :].strip()
        words = re.findall(r"[A-Za-z0-9'-]+", first_line)
        if not words:
            return "modern living"
        return " ".join(words[:5])


MockLLMClient = DeterministicMockLLMClient

_PLACEHOLDER_PROJECTS: frozenset[str] = frozenset(
    {
        "",
        "local-dev-project",
        "your-gcp-project-id",
        "test-project-bwg",
        "pitch-generator-dev",
    }
)

_PLACEHOLDER_BUCKET_PREFIXES: tuple[str, ...] = (
    "test-",
    "local-dev-project",
    "your-gcp-project-id",
    "pitch-generator-dev",
)


def _is_offline_test_mode(project_id: str | None = None) -> bool:
    """
    /**
     * Determine whether explicit offline/test mode is active.
     *
     * Why: Ensures `DeterministicMockLLMClient` is only used during `pytest` runs or
     * when `PITCH_OFFLINE_MODE=1` (`--offline`) is explicitly set, preventing live
     * CLI or browser runs from silently masking cloud/model errors with mock outputs.
     */
    """
    if (
        os.environ.get("PITCH_OFFLINE_MODE") == "1"
        or "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in sys.modules
    ):
        return True
    if project_id is not None and project_id.strip() == "test-project-bwg":
        return True
    return False


def _is_live_cloud_configured(
    *,
    project_id: str | None = None,
    bucket_name: str | None = None,
) -> bool:
    """
    /**
     * Check whether live Google Cloud SDK initialization should run in the current environment.
     *
     * Why: Prevents offline `pytest` runs or unconfigured placeholder environments from
     * attempting external metadata server or Google Cloud API calls, while enabling live
     * Gemini Enterprise Agent Platform and Cloud Storage clients automatically when real
     * cloud settings are present.
     *
     * @param project_id Optional GCP project ID to validate against known test placeholders.
     * @param bucket_name Optional GCS bucket name to validate against known test prefixes.
     * @return `True` if live Google Cloud SDK clients should be initialized.
     */
    """
    if _is_offline_test_mode(project_id):
        return False
    if project_id is not None:
        clean_proj = project_id.strip()
        if clean_proj in _PLACEHOLDER_PROJECTS:
            return False
    if bucket_name is not None:
        clean_bucket = bucket_name.strip()
        if not clean_bucket or clean_bucket.startswith(_PLACEHOLDER_BUCKET_PREFIXES):
            return False
    return True


class EnterpriseGenAILLMClient:
    """
    /**
     * Production adapter for Gemini Enterprise Agent Platform (`google.genai.Client`)
     * with offline test support via `DeterministicMockLLMClient`.
     *
     * Why: Invokes live Gemini models on Vertex AI when running in the CLI or Cloud Run,
     * applying:
     *   - A1: Exponential backoff with jitter on `429 RESOURCE_EXHAUSTED` / transient errors,
     *   - A2: Inter-call pacing between consecutive live requests to avoid sub-second bursts,
     *   - A3: In-memory prompt deduplication/caching across retries and repeat briefs,
     * while supporting deterministic execution when `--offline` (`PITCH_OFFLINE_MODE=1`)
     * or `pytest` is active.
     */
    """

    _RATE_LOCK = threading.Lock()
    _last_live_call_ts: float = 0.0
    _LIVE_TEXT_CACHE: dict[tuple[str, str, str, float], str] = {}
    _LIVE_IMAGE_CACHE: dict[tuple[str, str], tuple[bytes, str]] = {}
    _MAX_CACHE_ENTRIES: int = 256

    def __init__(
        self,
        config: PitchConfig | None = None,
        sdk_client: Any = None,
        fallback_client: LLMClientProtocol | None = None,
        *,
        max_retries: int | None = None,
        base_retry_delay_sec: float | None = None,
        min_call_interval_sec: float | None = None,
        enable_cache: bool = True,
    ) -> None:
        """
        /**
         * Initialize the Gemini Enterprise Agent Platform LLM client wrapper.
         *
         * @param config Resolved `PitchConfig` instance.
         * @param sdk_client Optional `google.genai.Client` instance.
         * @param fallback_client Offline fallback `LLMClientProtocol` implementation.
         * @param max_retries Maximum retry attempts on 429/transient errors (default 4).
         * @param base_retry_delay_sec Initial backoff delay in seconds before exponential scaling.
         * @param min_call_interval_sec Minimum spacing in seconds between consecutive live SDK calls.
         * @param enable_cache Whether to deduplicate identical prompts via in-memory cache.
         */
        """
        self.config = config or get_config()
        self._has_custom_fallback = fallback_client is not None
        self._is_custom_sdk = sdk_client is not None
        self.fallback_client: LLMClientProtocol = fallback_client or DeterministicMockLLMClient(
            self.config
        )
        self.calls: list[dict[str, Any]] = []
        self.cache_hits: int = 0
        self.retry_count: int = 0
        self._init_error: str | None = None

        env_retries = os.environ.get("PITCH_MAX_RETRIES")
        self.max_retries: int = (
            max_retries
            if max_retries is not None
            else (int(env_retries) if env_retries and env_retries.isdigit() else 4)
        )
        self.base_retry_delay_sec: float = (
            base_retry_delay_sec
            if base_retry_delay_sec is not None
            else (0.01 if self._is_custom_sdk else 2.0)
        )
        env_interval = os.environ.get("PITCH_MIN_CALL_INTERVAL_SEC")
        if min_call_interval_sec is not None:
            self.min_call_interval_sec = float(min_call_interval_sec)
        elif env_interval is not None:
            try:
                self.min_call_interval_sec = max(0.0, float(env_interval))
            except ValueError:
                self.min_call_interval_sec = 1.2
        else:
            self.min_call_interval_sec = 0.0 if self._is_custom_sdk else 1.2

        self.enable_cache: bool = enable_cache
        self.text_cache: dict[tuple[str, str, str, float], str] = (
            {} if self._is_custom_sdk else self._LIVE_TEXT_CACHE
        )
        self.image_cache: dict[tuple[str, str], tuple[bytes, str]] = (
            {} if self._is_custom_sdk else self._LIVE_IMAGE_CACHE
        )

        if sdk_client is not None:
            self.sdk_client = sdk_client
        elif _is_live_cloud_configured(project_id=self.config.project_id):
            self.sdk_client = self._init_default_sdk_client()
        else:
            self.sdk_client = None

    @classmethod
    def clear_cache(cls) -> None:
        """
        /**
         * Clear the process-wide in-memory text and image deduplication caches.
         *
         * Why: Allows tests and callers to reset cached Vertex AI responses between runs.
         */
        """
        with cls._RATE_LOCK:
            cls._LIVE_TEXT_CACHE.clear()
            cls._LIVE_IMAGE_CACHE.clear()

    def _init_default_sdk_client(self) -> Any:
        """
        /**
         * Instantiate a live `google.genai.Client` bound to the configured GCP project and location.
         *
         * Why: Connects `EnterpriseGenAILLMClient` to the Gemini Enterprise Agent Platform
         * using the project and location resolved by `.env` and `PitchConfig`.
         *
         * @return Initialized `google.genai.Client` instance, or `None` if initialization fails.
         */
        """
        try:
            from google import genai

            return genai.Client(
                vertexai=True,
                project=self.config.project_id,
                location=self.config.location,
            )
        except Exception as exc:
            self._init_error = str(exc)
            return None

    def _pace_live_call(self) -> None:
        """
        /**
         * Enforce minimum spacing between consecutive live Vertex AI calls (A2).
         *
         * Why: A single pitch workflow executes 3 to 5 agent turns sequentially. Smoothing
         * bursts with a ~1.2s minimum interval avoids tripping sub-minute Vertex AI rate buckets.
         */
        """
        if self.min_call_interval_sec <= 0.0:
            return
        if not self._is_custom_sdk and _is_offline_test_mode(self.config.project_id):
            return
        with self._RATE_LOCK:
            now = time.monotonic()
            elapsed = now - EnterpriseGenAILLMClient._last_live_call_ts
            if (
                EnterpriseGenAILLMClient._last_live_call_ts > 0.0
                and elapsed < self.min_call_interval_sec
            ):
                wait_sec = self.min_call_interval_sec - elapsed
                time.sleep(wait_sec)
            EnterpriseGenAILLMClient._last_live_call_ts = time.monotonic()

    @staticmethod
    def _is_retryable_quota_error(exc: Exception) -> bool:
        """Return True if `exc` represents a 429 RESOURCE_EXHAUSTED or transient 503 error."""
        msg = str(exc).lower()
        retry_markers = (
            "429",
            "resource_exhausted",
            "resource exhausted",
            "quota",
            "rate limit",
            "too many requests",
            "503",
            "unavailable",
        )
        return any(marker in msg for marker in retry_markers)

    def _call_with_retry(self, operation: str, model: str, fn: Callable[[], Any]) -> Any:
        """
        /**
         * Execute an SDK call with inter-call pacing (A2) and exponential backoff + jitter
         * on `429 RESOURCE_EXHAUSTED` / transient errors (A1).
         */
        """
        attempt = 0
        while True:
            self._pace_live_call()
            try:
                return fn()
            except Exception as exc:
                if attempt < self.max_retries and self._is_retryable_quota_error(exc):
                    attempt += 1
                    self.retry_count += 1
                    jitter = (
                        random.uniform(0.1, 0.75)
                        if self.base_retry_delay_sec >= 0.5
                        else 0.0
                    )
                    delay = min(
                        16.0,
                        self.base_retry_delay_sec * (2 ** (attempt - 1)) + jitter,
                    )
                    print(
                        f"[EnterpriseGenAILLMClient] Transient rate limit ({operation} on {model}); "
                        f"retrying in {delay:.2f}s (attempt {attempt}/{self.max_retries})...",
                        flush=True,
                    )
                    time.sleep(delay)
                    continue
                raise

    def _raise_if_not_offline(self, operation: str, model: str, detail: str) -> None:
        """Raise an actionable RuntimeError unless explicit offline/test mode is active."""
        if _is_offline_test_mode(self.config.project_id) or self._has_custom_fallback:
            return
        raise RuntimeError(
            f"[Vertex AI / Gemini Error] {operation} failed for model '{model}' "
            f"(project='{self.config.project_id}', location='{self.config.location}'): {detail}. "
            f"Check your .env configuration, network access, and GCP authentication."
        )

    def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: str = "",
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """
        /**
         * Generate text via the live `google.genai.Client` (or injected SDK client), falling back
         * to `fallback_client` only when running in explicit offline/test mode.
         */
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must not be empty")

        clean_prompt = prompt.strip()
        clean_sys = (system_instruction or "").strip()
        resolved_model = model or self.config.flash_model
        self.calls.append(
            {
                "type": "text",
                "prompt": clean_prompt,
                "system_instruction": system_instruction,
                "model": resolved_model,
                "temperature": temperature,
            }
        )

        cache_key = (resolved_model, clean_sys, clean_prompt, round(float(temperature), 3))
        if self.enable_cache and cache_key in self.text_cache:
            self.cache_hits += 1
            return self.text_cache[cache_key]

        if self.sdk_client is not None:
            if hasattr(self.sdk_client, "generate_text"):
                out = str(
                    self._call_with_retry(
                        "generate_text",
                        resolved_model,
                        lambda: self.sdk_client.generate_text(
                            clean_prompt,
                            system_instruction=system_instruction,
                            model=resolved_model,
                            temperature=temperature,
                        ),
                    )
                )
                if self.enable_cache and out:
                    if len(self.text_cache) >= self._MAX_CACHE_ENTRIES:
                        self.text_cache.pop(next(iter(self.text_cache)), None)
                    self.text_cache[cache_key] = out
                return out
            if hasattr(self.sdk_client, "models") and hasattr(
                self.sdk_client.models, "generate_content"
            ):
                try:
                    gen_config: Any = {"temperature": temperature}
                    if system_instruction:
                        gen_config["system_instruction"] = system_instruction
                    try:
                        from google.genai import types as genai_types

                        gen_config = genai_types.GenerateContentConfig(
                            system_instruction=system_instruction or None,
                            temperature=temperature,
                        )
                    except Exception:
                        pass

                    response = self._call_with_retry(
                        "generate_content",
                        resolved_model,
                        lambda: self.sdk_client.models.generate_content(
                            model=resolved_model,
                            contents=clean_prompt,
                            config=gen_config,
                        ),
                    )
                    text_out = getattr(response, "text", None)
                    if not (text_out and str(text_out).strip()):
                        extracted_parts: list[str] = []
                        for cand in getattr(response, "candidates", None) or []:
                            content_obj = getattr(cand, "content", None)
                            for part in getattr(content_obj, "parts", None) or []:
                                part_txt = getattr(part, "text", None)
                                if part_txt and str(part_txt).strip():
                                    extracted_parts.append(str(part_txt).strip())
                                fn_call = getattr(part, "function_call", None)
                                fn_args = getattr(fn_call, "args", None) if fn_call else None
                                if isinstance(fn_args, dict):
                                    for key in ("art_direction", "prompt", "text", "content"):
                                        val = fn_args.get(key)
                                        if isinstance(val, str) and val.strip():
                                            extracted_parts.append(val.strip())
                        if extracted_parts:
                            text_out = "\n\n".join(extracted_parts)
                    if text_out and str(text_out).strip():
                        clean_out = str(text_out).strip()
                        if self.enable_cache:
                            if len(self.text_cache) >= self._MAX_CACHE_ENTRIES:
                                self.text_cache.pop(next(iter(self.text_cache)), None)
                            self.text_cache[cache_key] = clean_out
                        return clean_out
                    self._raise_if_not_offline(
                        "generate_content",
                        resolved_model,
                        "Model returned an empty text response",
                    )
                except RuntimeError:
                    raise
                except Exception as exc:
                    print(
                        f"[EnterpriseGenAILLMClient] generate_content failed ({resolved_model}): {exc}",
                        flush=True,
                    )
                    self._raise_if_not_offline("generate_content", resolved_model, str(exc))
        else:
            reason = (
                self._init_error
                or f"PROJECT_ID is set to placeholder '{self.config.project_id}' instead of a valid GCP project"
            )
            self._raise_if_not_offline("SDK initialization", resolved_model, reason)

        return self.fallback_client.generate_text(
            clean_prompt,
            system_instruction=system_instruction,
            model=resolved_model,
            temperature=temperature,
        )

    def generate_image(
        self,
        prompt: str,
        *,
        model: str | None = None,
    ) -> tuple[bytes, str]:
        """
        /**
         * Generate an image via the live `google.genai.Client` (or injected SDK client),
         * falling back to `fallback_client` only when running in explicit offline/test mode.
         */
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must not be empty")

        clean_prompt = prompt.strip()
        resolved_model = model or self.config.image_model
        self.calls.append(
            {
                "type": "image",
                "prompt": clean_prompt,
                "model": resolved_model,
            }
        )

        img_cache_key = (resolved_model, clean_prompt)
        if self.enable_cache and img_cache_key in self.image_cache:
            self.cache_hits += 1
            return self.image_cache[img_cache_key]

        if self.sdk_client is not None:
            if hasattr(self.sdk_client, "generate_image"):
                data, mime = self._call_with_retry(
                    "generate_image",
                    resolved_model,
                    lambda: self.sdk_client.generate_image(
                        clean_prompt, model=resolved_model
                    ),
                )
                result_pair = (bytes(data), str(mime))
                if self.enable_cache and result_pair[0]:
                    if len(self.image_cache) >= self._MAX_CACHE_ENTRIES:
                        self.image_cache.pop(next(iter(self.image_cache)), None)
                    self.image_cache[img_cache_key] = result_pair
                return result_pair
            if hasattr(self.sdk_client, "models"):
                last_err: str | None = None
                if "imagen" in resolved_model.lower() and hasattr(
                    self.sdk_client.models, "generate_images"
                ):
                    try:
                        img_resp = self._call_with_retry(
                            "generate_images",
                            resolved_model,
                            lambda: self.sdk_client.models.generate_images(
                                model=resolved_model,
                                prompt=clean_prompt,
                            ),
                        )
                        gen_imgs = getattr(img_resp, "generated_images", None) or []
                        if gen_imgs:
                            first_img = getattr(gen_imgs[0], "image", None)
                            raw_bytes = getattr(first_img, "image_bytes", None)
                            mime = getattr(first_img, "mime_type", None) or "image/png"
                            if raw_bytes:
                                result_pair = (bytes(raw_bytes), str(mime))
                                if self.enable_cache:
                                    if len(self.image_cache) >= self._MAX_CACHE_ENTRIES:
                                        self.image_cache.pop(next(iter(self.image_cache)), None)
                                    self.image_cache[img_cache_key] = result_pair
                                return result_pair
                    except Exception as exc:
                        last_err = str(exc)

                if hasattr(self.sdk_client.models, "generate_content"):
                    try:
                        img_config: Any = {"response_modalities": ["IMAGE"]}
                        try:
                            from google.genai import types as genai_types

                            img_config = genai_types.GenerateContentConfig(
                                response_modalities=["IMAGE"],
                                image_config=genai_types.ImageConfig(aspect_ratio="16:9"),
                            )
                        except Exception:
                            pass

                        resp = self._call_with_retry(
                            "generate_image",
                            resolved_model,
                            lambda: self.sdk_client.models.generate_content(
                                model=resolved_model,
                                contents=clean_prompt,
                                config=img_config,
                            ),
                        )
                        for candidate in getattr(resp, "candidates", None) or []:
                            content = getattr(candidate, "content", None)
                            for part in getattr(content, "parts", None) or []:
                                inline_data = getattr(part, "inline_data", None)
                                data_bytes = getattr(inline_data, "data", None)
                                if data_bytes:
                                    mime = (
                                        getattr(inline_data, "mime_type", None)
                                        or "image/png"
                                    )
                                    result_pair = (bytes(data_bytes), str(mime))
                                    if self.enable_cache:
                                        if len(self.image_cache) >= self._MAX_CACHE_ENTRIES:
                                            self.image_cache.pop(next(iter(self.image_cache)), None)
                                        self.image_cache[img_cache_key] = result_pair
                                    return result_pair
                        self._raise_if_not_offline(
                            "generate_image",
                            resolved_model,
                            last_err or "Model response did not contain image bytes",
                        )
                    except RuntimeError:
                        raise
                    except Exception as exc:
                        print(
                            f"[EnterpriseGenAILLMClient] generate_image failed ({resolved_model}): {exc}",
                            flush=True,
                        )
                        self._raise_if_not_offline("generate_image", resolved_model, str(exc))
        else:
            reason = (
                self._init_error
                or f"PROJECT_ID is set to placeholder '{self.config.project_id}' instead of a valid GCP project"
            )
            self._raise_if_not_offline("SDK initialization", resolved_model, reason)

        return self.fallback_client.generate_image(clean_prompt, model=resolved_model)


@dataclass
class ArtifactRecord:
    """
    /**
     * Versioned binary artifact record persisted by an `ArtifactServiceProtocol`.
     *
     * Why: Tracks filename, monotonic version number, raw binary payload, MIME type,
     * and optional Cloud Storage `gs://` URI (`gcs_uri`) so both in-memory and GCS
     * artifact services return a uniform structure (`PROJECT.md` Interface Contract 2).
     *
     * @param filename Logical artifact filename (e.g., `"key_visual.png"`).
     * @param version Monotonically increasing integer version starting at 1.
     * @param data Raw binary artifact bytes.
     * @param mime_type MIME type string (default `"image/png"`).
     * @param gcs_uri Full `gs://<bucket>/...` URI when backed by Cloud Storage, else `None`.
     */
    """

    filename: str
    version: int
    data: bytes
    mime_type: str = "image/png"
    gcs_uri: str | None = None

    def to_metadata_dict(self) -> dict[str, Any]:
        """
        /**
         * Serialize artifact metadata without duplicating large binary blobs in JSON logs.
         *
         * Why: REST and telemetry payloads need artifact version, size, MIME type, and
         * `gcs_uri` in JSON format without embedding megabytes of raw bytes.
         *
         * @return Metadata dictionary for JSON responses.
         */
        """
        return {
            "filename": self.filename,
            "version": self.version,
            "bytes": len(self.data),
            "mime_type": self.mime_type,
            "gcs_uri": self.gcs_uri,
        }


@runtime_checkable
class ArtifactServiceProtocol(Protocol):
    """
    /**
     * Protocol for persisting and retrieving versioned binary campaign artifacts.
     *
     * Why: Enables `get_artifact_service()` to swap transparently between
     * `InMemoryArtifactService` (for local/ephemeral runs) and `GcsArtifactService`
     * (when `LOGS_BUCKET_NAME` is configured for durable Cloud Storage persistence).
     */
    """

    def save_artifact(
        self,
        filename: str,
        data: bytes,
        mime_type: str = "image/png",
        session_id: str = "default",
    ) -> ArtifactRecord:
        """
        /**
         * Save a new version of `filename` under `session_id`.
         *
         * Why: Automatically increments version numbers so iterative key visual passes
         * never overwrite audit history.
         *
         * @param filename Artifact file name.
         * @param data Non-empty binary payload.
         * @param mime_type MIME type string.
         * @param session_id Session identifier owning the artifact.
         * @return Persisted `ArtifactRecord`.
         */
        """
        ...

    def get_artifact(
        self,
        filename: str,
        session_id: str = "default",
    ) -> ArtifactRecord | None:
        """
        /**
         * Retrieve the latest version of `filename` for `session_id`.
         *
         * Why: Allows CLI clients and HTTP endpoints to serve the most recent key visual.
         *
         * @param filename Artifact file name to look up.
         * @param session_id Session identifier.
         * @return Latest `ArtifactRecord` or `None` if not found.
         */
        """
        ...

    def list_artifacts(self, session_id: str = "default") -> list[ArtifactRecord]:
        """
        /**
         * List all saved artifact versions for `session_id`.
         *
         * Why: Supports audit trails that inspect every version produced during a session.
         *
         * @param session_id Session identifier.
         * @return Chronological list of `ArtifactRecord` objects.
         */
        """
        ...


def _validate_artifact_inputs(filename: str, data: bytes, session_id: str) -> tuple[str, str]:
    """
    /**
     * Validate artifact filename, binary payload, and session ID before storage.
     *
     * Why: Rejects empty payloads and path traversal sequences (`..` or leading `/`)
     * to prevent malformed object keys or directory escape vulnerabilities.
     *
     * @param filename Target artifact filename.
     * @param data Binary payload bytes.
     * @param session_id Session identifier.
     * @return Tuple of `(clean_filename, clean_session_id)`.
     */
    """
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename must not be empty")
    clean_name = filename.strip()
    if ".." in clean_name or clean_name.startswith(("/", "\\")):
        raise ValueError(f"Invalid artifact filename {filename!r}: path traversal is forbidden")
    if not isinstance(data, (bytes, bytearray)) or len(data) == 0:
        raise ValueError("Artifact data must not be empty")
    clean_session = (session_id or "default").strip() or "default"
    return (clean_name, clean_session)


class InMemoryArtifactService:
    """
    /**
     * Ephemeral in-memory implementation of `ArtifactServiceProtocol`.
     *
     * Why: Used as the default starter app artifact store when `LOGS_BUCKET_NAME` is
     * unset, matching ADK's `InMemoryArtifactService` behavior while keeping local
     * unit tests fast and self-contained.
     */
    """

    def __init__(self) -> None:
        """
        /**
         * Initialize empty versioned artifact storage dictionaries.
         *
         * Why: Isolates artifact versions per `(session_id, filename)` pair.
         */
        """
        self._by_session_file: dict[tuple[str, str], list[ArtifactRecord]] = {}
        self._by_session: dict[str, list[ArtifactRecord]] = {}

    def save_artifact(
        self,
        filename: str,
        data: bytes,
        mime_type: str = "image/png",
        session_id: str = "default",
    ) -> ArtifactRecord:
        """
        /**
         * Save a binary artifact in memory and increment its version number.
         *
         * Why: Preserves every version in memory (`version = 1, 2, ...`) with `gcs_uri=None`
         * to reflect non-GCS ephemeral storage.
         *
         * @param filename Artifact filename.
         * @param data Non-empty binary bytes.
         * @param mime_type MIME type string.
         * @param session_id Session identifier.
         * @return Newly created `ArtifactRecord`.
         */
        """
        clean_name, clean_session = _validate_artifact_inputs(filename, data, session_id)
        key = (clean_session, clean_name)
        history = self._by_session_file.setdefault(key, [])
        next_version = len(history) + 1
        record = ArtifactRecord(
            filename=clean_name,
            version=next_version,
            data=bytes(data),
            mime_type=mime_type or "image/png",
            gcs_uri=None,
        )
        history.append(record)
        self._by_session.setdefault(clean_session, []).append(record)
        return record

    def get_artifact(
        self,
        filename: str,
        session_id: str = "default",
    ) -> ArtifactRecord | None:
        """
        /**
         * Return the most recent `ArtifactRecord` for `(session_id, filename)`.
         *
         * Why: Enables callers to fetch the latest generated key visual by filename.
         *
         * @param filename Artifact filename.
         * @param session_id Session identifier.
         * @return Latest `ArtifactRecord` or `None`.
         */
        """
        clean_session = (session_id or "default").strip() or "default"
        clean_name = (filename or "").strip()
        history = self._by_session_file.get((clean_session, clean_name), [])
        return history[-1] if history else None

    def list_artifacts(self, session_id: str = "default") -> list[ArtifactRecord]:
        """
        /**
         * Return all `ArtifactRecord` versions saved under `session_id`.
         *
         * Why: Allows tests and telemetry auditors to inspect the full version history.
         *
         * @param session_id Session identifier.
         * @return List of `ArtifactRecord` instances for the session.
         */
        """
        clean_session = (session_id or "default").strip() or "default"
        return list(self._by_session.get(clean_session, []))


class GcsArtifactService:
    """
    /**
     * Cloud Storage-backed implementation of `ArtifactServiceProtocol`.
     *
     * Why: Persists generated key visuals to `gs://<bucket_name>/key-visuals/...` so
     * visual artifacts survive container restarts and can be referenced by BigQuery
     * `ObjectRef` (`OBJ.MAKE_REF` / `OBJ.FETCH_METADATA`) tables in Module 2.
     */
    """

    def __init__(
        self,
        bucket_name: str,
        client: Any = None,
        prefix: str = "key-visuals",
    ) -> None:
        """
        /**
         * Initialize the Cloud Storage artifact service.
         *
         * Why: Normalizes `bucket_name` (stripping any accidental `gs://` prefix) and
         * accepts an optional injected GCS `client` for offline mock verification.
         *
         * @param bucket_name Target Cloud Storage bucket name.
         * @param client Optional `google.cloud.storage.Client` (or mock) instance.
         * @param prefix Object key prefix inside the bucket (default `"key-visuals"`).
         */
        """
        normalized = normalize_bucket_name(bucket_name)
        if not normalized:
            raise ValueError("bucket_name must not be empty for GcsArtifactService")
        self.bucket_name = normalized
        if client is not None:
            self.client = client
        elif _is_live_cloud_configured(bucket_name=normalized):
            self.client = self._init_default_storage_client()
        else:
            self.client = None
        self.prefix = prefix.strip("/") or "key-visuals"
        self._by_session_file: dict[tuple[str, str], list[ArtifactRecord]] = {}
        self._by_session: dict[str, list[ArtifactRecord]] = {}
        self.uploaded_blobs: list[dict[str, Any]] = []

    def _init_default_storage_client(self) -> Any:
        """
        /**
         * Instantiate a live `google.cloud.storage.Client` for uploading artifacts to GCS.
         *
         * Why: Connects `GcsArtifactService` to Google Cloud Storage when `LOGS_BUCKET_NAME`
         * is configured for a real project bucket, while gracefully returning `None` if
         * `google-cloud-storage` or credentials are unavailable.
         *
         * @return Initialized `google.cloud.storage.Client` instance, or `None`.
         */
        """
        try:
            from google.cloud import storage

            cfg = get_config()
            project = (
                cfg.project_id
                if _is_live_cloud_configured(project_id=cfg.project_id)
                else None
            )
            return storage.Client(project=project)
        except Exception:
            return None

    def save_artifact(
        self,
        filename: str,
        data: bytes,
        mime_type: str = "image/png",
        session_id: str = "default",
    ) -> ArtifactRecord:
        """
        /**
         * Persist a versioned binary artifact to Cloud Storage and return its `gs://` URI.
         *
         * Why: Constructs a canonical `gs://<bucket>/<prefix>/<filename>` URI matching
         * BigQuery `bwg.key_visuals` (`OBJ.MAKE_REF`), increments the per-session version
         * counter, and uploads via `client.upload_bytes(...)` or `bucket().blob().upload_from_string(...)`.
         *
         * @param filename Artifact filename (e.g., `"key_visual.png"`, `"cats.png"`).
         * @param data Non-empty binary image bytes.
         * @param mime_type MIME type string (default `"image/png"`).
         * @param session_id Session or campaign identifier.
         * @return `ArtifactRecord` populated with `gcs_uri = "gs://<bucket>/<prefix>/<filename>"`.
         */
        """
        clean_name, clean_session = _validate_artifact_inputs(filename, data, session_id)
        clean_mime = (mime_type or "image/png").strip() or "image/png"
        raw_bytes = bytes(data)

        key = (clean_session, clean_name)
        history = self._by_session_file.setdefault(key, [])
        next_version = len(history) + 1

        object_path = f"{self.prefix}/{clean_name}"
        gcs_uri = f"gs://{self.bucket_name}/{object_path}"

        if self.client is not None:
            if hasattr(self.client, "upload_bytes"):
                self.client.upload_bytes(
                    bucket_name=self.bucket_name,
                    object_path=object_path,
                    data=raw_bytes,
                    mime_type=clean_mime,
                )
            elif hasattr(self.client, "bucket"):
                try:
                    bucket_obj = self.client.bucket(self.bucket_name)
                    blob_obj = bucket_obj.blob(object_path)
                    if hasattr(blob_obj, "upload_from_string"):
                        blob_obj.upload_from_string(raw_bytes, content_type=clean_mime)
                except Exception:
                    pass

        self.uploaded_blobs.append(
            {
                "bucket": self.bucket_name,
                "object_path": object_path,
                "gcs_uri": gcs_uri,
                "version": next_version,
                "bytes": len(raw_bytes),
                "mime_type": clean_mime,
            }
        )

        record = ArtifactRecord(
            filename=clean_name,
            version=next_version,
            data=raw_bytes,
            mime_type=clean_mime,
            gcs_uri=gcs_uri,
        )
        history.append(record)
        self._by_session.setdefault(clean_session, []).append(record)
        return record

    def get_artifact(
        self,
        filename: str,
        session_id: str = "default",
        version: int | None = None,
    ) -> ArtifactRecord | None:
        """
        /**
         * Retrieve the latest (or specific version) of `filename` for `session_id` from the GCS service.
         *
         * Why: Returns the most recently persisted `ArtifactRecord` (or a specific historical
         * revision when `version` is supplied) including its `gcs_uri`.
         *
         * @param filename Artifact filename.
         * @param session_id Session identifier.
         * @param version Optional 1-based version number; defaults to latest.
         * @return Matching `ArtifactRecord` or `None`.
         */
        """
        if not isinstance(filename, str) or not filename.strip():
            return None
        clean_session = (session_id or "default").strip() or "default"
        clean_name = filename.strip()
        history = self._by_session_file.get((clean_session, clean_name), [])
        if not history:
            return None
        if version is None:
            return history[-1]
        for rec in history:
            if rec.version == version:
                return rec
        return None

    def list_artifacts(self, session_id: str = "default") -> list[ArtifactRecord]:
        """
        /**
         * List all saved artifact records for `session_id`.
         *
         * Why: Supports enumerating every versioned `gs://` URI generated during a session.
         *
         * @param session_id Session identifier.
         * @return List of `ArtifactRecord` objects.
         */
        """
        clean_session = (session_id or "default").strip() or "default"
        return list(self._by_session.get(clean_session, []))


def get_artifact_service(
    config: PitchConfig | None = None,
    client: Any = None,
    *,
    bucket_name: str | None = None,
    env: Mapping[str, str] | None = None,
) -> ArtifactServiceProtocol:
    """
    /**
     * Select `GcsArtifactService` when a bucket is configured via `bucket_name`, `env`, or `config`,
     * and fall back to `InMemoryArtifactService` when empty.
     *
     * Why: Provides environment-driven Cloud Storage persistence (`LOGS_BUCKET_NAME`) so local
     * development works with zero configuration while staging/production persists to GCS (`gs://<bucket>/key-visuals/...`).
     *
     * @param config Optional `PitchConfig` instance.
     * @param client Optional Cloud Storage client for dependency injection.
     * @param bucket_name Explicit bucket name override.
     * @param env Optional environment dictionary containing `LOGS_BUCKET_NAME`.
     * @return Configured `GcsArtifactService` or `InMemoryArtifactService`.
     */
    """
    if bucket_name is not None:
        raw_bucket = bucket_name
    elif env is not None:
        raw_bucket = env.get("LOGS_BUCKET_NAME", "")
    elif config is not None:
        raw_bucket = config.logs_bucket_name or ""
    else:
        raw_bucket = os.environ.get("LOGS_BUCKET_NAME") or get_config().logs_bucket_name or ""

    normalized = normalize_bucket_name(raw_bucket)
    if normalized:
        return GcsArtifactService(bucket_name=normalized, client=client)
    return InMemoryArtifactService()


create_artifact_service = get_artifact_service
select_artifact_service = get_artifact_service
resolve_artifact_service = get_artifact_service
