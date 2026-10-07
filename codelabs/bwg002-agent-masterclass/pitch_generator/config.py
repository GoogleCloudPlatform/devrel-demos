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
 * @file config.py
 * @description Centralized runtime configuration resolver for the Pitch Generator app.
 *
 * Why: Consolidates all environment variable parsing, local `.env` and `gcloud` discovery,
 * Gemini Enterprise Agent Platform configuration (`GOOGLE_GENAI_USE_ENTERPRISE`), Cloud
 * Storage bucket normalization, and model tier defaults into an immutable,
 * dependency-injectable configuration object (`PitchConfig`). This avoids scattering
 * hardcoded model version strings or raw `os.environ` lookups across agent modules.
 */
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import functools
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

DEFAULT_FLASH_MODEL = "gemini-3.8-flash"
DEFAULT_IMAGE_MODEL = "gemini-nano-banana-2.1"
DEFAULT_LOCAL_MODEL = "gemma-3-4b-it"

VALID_ROUTING_MODES: tuple[str, ...] = (
    "auto",
    "cloud_frontier",
)

_REPO_ROOT: Path = Path(__file__).resolve().parent.parent


class ConfigurationError(ValueError):
    """
    /**
     * Exception raised when `PitchConfig` validation detects invalid or missing settings.
     *
     * Why: Subclasses `ValueError` so callers catching standard validation errors handle
     * configuration problems uniformly while allowing targeted `except ConfigurationError:`
     * handling during startup.
     */
    """


def normalize_bucket_name(raw_bucket: str | None) -> str:
    """
    /**
     * Normalize a Cloud Storage bucket identifier into a bare bucket name.
     *
     * Why: Learners and deployment scripts sometimes pass `gs://my-bucket/` instead of
     * `my-bucket`. `GcsArtifactService` requires a bare bucket name without a scheme
     * prefix or trailing slash, so normalizing at the configuration boundary prevents
     * invalid GCS object paths.
     *
     * @param raw_bucket Raw bucket name or `gs://` URI string.
     * @return Stripped bare bucket name (or empty string if unset).
     */
    """
    if not raw_bucket:
        return ""
    cleaned = raw_bucket.strip()
    if cleaned.startswith("gs://"):
        cleaned = cleaned[len("gs://") :]
    cleaned = cleaned.strip("/")
    if "/" in cleaned:
        cleaned = cleaned.split("/", 1)[0]
    return cleaned.strip()


def _parse_bool_flag(raw_value: str | None) -> bool | None:
    """
    /**
     * Parse an optional environment string into a boolean flag.
     *
     * Why: Environment variables may be written as `"TRUE"`, `"true"`, `"1"`, `"yes"`,
     * `"FALSE"`, `"0"`, or `"no"`. Returning `None` when unset or unrecognized lets
     * `get_config` evaluate fallback variables deterministically.
     *
     * @param raw_value Raw environment variable value.
     * @return Parsed boolean or `None` if empty/unrecognized.
     */
    """
    if raw_value is None:
        return None
    normalized = raw_value.strip().lower()
    if not normalized:
        return None
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    return False


def _load_dotenv_file(dotenv_path: Path | None = None) -> dict[str, str]:
    """
    /**
     * Parse key-value pairs from `<repo_root>/.env` or `~/.env` if present.
     *
     * Why: When learners or background tools run the Python server without first sourcing
     * `setenv.sh` in the same subshell, loading `.env` automatically ensures the process
     * still discovers `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`, and `LOGS_BUCKET_NAME`.
     *
     * @param dotenv_path Optional explicit `.env` file path override.
     * @return Dictionary of parsed environment variables.
     */
    """
    candidates = (
        [dotenv_path]
        if dotenv_path is not None
        else [_REPO_ROOT / ".env", Path.home() / ".env"]
    )
    parsed: dict[str, str] = {}
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            try:
                for raw_line in candidate.read_text(encoding="utf-8").splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[len("export ") :].strip()
                    key, val = line.split("=", 1)
                    clean_key = key.strip()
                    clean_val = val.strip().strip('"').strip("'")
                    if clean_key:
                        parsed[clean_key] = clean_val
                break
            except OSError:
                continue
    return parsed


@functools.lru_cache(maxsize=4)
def _discover_gcloud_value(config_key: str) -> str:
    """
    /**
     * Query the `gcloud` CLI once per process for a configuration property (such as
     * `project` or `compute/region`).
     *
     * Why: Enables local runs on a provisioned Google Cloud VM to automatically discover
     * the active project ID and region even if `.env` has not been generated yet, while
     * skipping external subprocess calls when `PITCH_OFFLINE_MODE=1`.
     *
     * @param config_key `gcloud config get-value` key name.
     * @return Discovered configuration string or empty string if unavailable.
     */
    """
    if os.environ.get("PITCH_OFFLINE_MODE") == "1":
        return ""
    gcloud_bin = shutil.which("gcloud")
    if not gcloud_bin:
        return ""
    try:
        proc = subprocess.run(
            [gcloud_bin, "config", "get-value", config_key],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
        if proc.returncode == 0:
            val = proc.stdout.strip()
            if val and val != "(unset)":
                return val
    except Exception:
        return ""
    return ""


@dataclass(frozen=True)
class PitchConfig:
    """
    /**
     * Immutable runtime configuration container for the Pitch Generator service.
     *
     * Why: Freezing configuration attributes guarantees thread safety and prevents
     * accidental runtime mutation across concurrent multi-agent graph executions.
     *
     * @param project_id Google Cloud project ID hosting Agent Platform and BigQuery.
     * @param region Regional endpoint for Cloud Run, Cloud Storage, and BigQuery.
     * @param location Model endpoint location (`global` or regional) for GenAI calls.
     * @param use_enterprise Whether Gemini Enterprise Agent Platform mode is enabled.
     * @param logs_bucket_name Bare Cloud Storage bucket name for artifact persistence.
     * @param visual_director_url Base HTTP URL for the remote A2A Visual Director service.
     * @param pitch_generator_url Base HTTP URL for the coordinator Pitch Generator service.
     * @param memory_bank_id Identifier for the Memory Bank session/memory store.
     * @param flash_model Gemini 3.8 Flash model identifier on Enterprise Agent Platform.
     * @param image_model Multimodal image generation model identifier (`gemini-nano-banana-2.1`).
     * @param local_model Local open-weights Gemma model identifier (used in Module 4).
     */
    """

    project_id: str = "local-dev-project"
    region: str = "us-central1"
    location: str = "global"
    use_enterprise: bool = True
    logs_bucket_name: str = ""
    visual_director_url: str = "http://localhost:8801"
    pitch_generator_url: str = "http://localhost:8080"
    memory_bank_id: str = "pitch-generator-memory"
    flash_model: str = DEFAULT_FLASH_MODEL
    image_model: str = DEFAULT_IMAGE_MODEL
    local_model: str = DEFAULT_LOCAL_MODEL

    def validate(self, *, require_project: bool = False) -> None:
        """
        /**
         * Validate that configuration fields satisfy structural invariants.
         *
         * Why: Fails fast with a descriptive `ConfigurationError` when URLs lack HTTP(S)
         * schemes or when a cloud deployment is missing a project ID.
         *
         * @param require_project If True, require `project_id` to be non-empty and not
         *   a placeholder.
         * @return None if valid; raises `ConfigurationError` otherwise.
         */
        """
        if require_project and (
            not self.project_id.strip() or self.project_id.strip() == "your-gcp-project-id"
        ):
            raise ConfigurationError("A valid Google Cloud project_id is required.")
        if not self.region.strip():
            raise ConfigurationError("region must not be empty.")
        if not self.location.strip():
            raise ConfigurationError("location must not be empty.")
        for label, url in (
            ("visual_director_url", self.visual_director_url),
            ("pitch_generator_url", self.pitch_generator_url),
        ):
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ConfigurationError(
                    f"{label} must start with 'http://' or 'https://', got {url!r}."
                )

    def to_public_dict(self) -> dict[str, Any]:
        """
        /**
         * Serialize non-sensitive configuration metadata for `GET /api/config`.
         *
         * Why: Exposes active project, region, Enterprise mode, and configured Cloud
         * models to the plain HTML/JS frontend without leaking internal credentials.
         *
         * @return Dictionary suitable for JSON serialization.
         */
        """
        modes = list(VALID_ROUTING_MODES)
        return {
            "project_id": self.project_id,
            "region": self.region,
            "location": self.location,
            "use_enterprise": self.use_enterprise,
            "logs_bucket_name": self.logs_bucket_name,
            "visual_director_url": self.visual_director_url,
            "pitch_generator_url": self.pitch_generator_url,
            "memory_bank_id": self.memory_bank_id,
            "models": {
                "flash": self.flash_model,
                "image": self.image_model,
            },
            "routing_modes": modes,
            "available_routing_modes": modes,
        }


def get_config(env: Mapping[str, str] | None = None) -> PitchConfig:
    """
    /**
     * Resolve a `PitchConfig` instance from an injected mapping, `.env`, `os.environ`,
     * or `gcloud` CLI discovery.
     *
     * Why: Accepting an optional `env` dictionary enables hermetic unit tests to verify
     * configuration resolution without mutating process-global environment variables,
     * while runtime calls (`env=None`) automatically merge `.env` and `gcloud` defaults
     * so local runs connect seamlessly to Gemini Enterprise Agent Platform.
     *
     * @param env Optional environment dictionary override (defaults to `os.environ` + `.env`).
     * @return Resolved immutable `PitchConfig` instance.
     */
    """
    if env is None:
        merged_env: dict[str, str] = _load_dotenv_file()
        merged_env.update(os.environ)
        source: Mapping[str, str] = merged_env
        allow_gcloud_fallback = True
    else:
        source = env
        allow_gcloud_fallback = False

    raw_project = (
        source.get("GOOGLE_CLOUD_PROJECT")
        or source.get("PROJECT_ID")
        or ""
    ).strip()
    if not raw_project and allow_gcloud_fallback:
        raw_project = _discover_gcloud_value("project")
    project_id = raw_project or "local-dev-project"

    raw_region = (
        source.get("GOOGLE_CLOUD_REGION")
        or source.get("REGION")
        or ""
    ).strip()
    if not raw_region and allow_gcloud_fallback:
        raw_region = _discover_gcloud_value("compute/region")
    region = raw_region or "us-central1"

    location = (
        source.get("GOOGLE_CLOUD_LOCATION")
        or source.get("LOCATION")
        or "global"
    ).strip() or "global"

    ent_flag = _parse_bool_flag(source.get("GOOGLE_GENAI_USE_ENTERPRISE"))
    use_enterprise = True if ent_flag is None else bool(ent_flag)

    logs_bucket_name = normalize_bucket_name(source.get("LOGS_BUCKET_NAME", ""))
    visual_director_url = (
        source.get("VISUAL_DIRECTOR_URL", "http://localhost:8801").strip()
        or "http://localhost:8801"
    ).rstrip("/")
    pitch_generator_url = (
        source.get("PITCH_GENERATOR_URL", "http://localhost:8080").strip()
        or "http://localhost:8080"
    ).rstrip("/")
    memory_bank_id = (
        source.get("MEMORY_BANK_ID", "pitch-generator-memory").strip()
        or "pitch-generator-memory"
    )

    flash_model = (source.get("FLASH_MODEL") or DEFAULT_FLASH_MODEL).strip()
    image_model = (source.get("IMAGE_MODEL") or DEFAULT_IMAGE_MODEL).strip()
    local_model = (source.get("LOCAL_MODEL") or DEFAULT_LOCAL_MODEL).strip()

    return PitchConfig(
        project_id=project_id,
        region=region,
        location=location,
        use_enterprise=use_enterprise,
        logs_bucket_name=logs_bucket_name,
        visual_director_url=visual_director_url,
        pitch_generator_url=pitch_generator_url,
        memory_bank_id=memory_bank_id,
        flash_model=flash_model,
        image_model=image_model,
        local_model=local_model,
    )
