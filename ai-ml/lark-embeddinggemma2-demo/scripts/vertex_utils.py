#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Shared Vertex AI EmbeddingGemma 2 and media utilities for Lark Memory scripts.
Centralizes endpoint configuration, gcloud token caching, text/batch embeddings,
media type detection, and deterministic local file ID generation.
"""

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

def _load_dotenv(dotenv_path=".env"):
    """Loads key=value pairs from a local .env file if present."""
    if not os.path.exists(dotenv_path):
        return
    try:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


_load_dotenv()

GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "YOUR_PROJECT_ID")
GOOGLE_CLOUD_REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
VERTEX_ENDPOINT_ID = os.environ.get("VERTEX_ENDPOINT_ID", "YOUR_ENDPOINT_ID")
GEMMA_3N_ENDPOINT_ID = os.environ.get(
    "GEMMA_3N_ENDPOINT_ID", "YOUR_GEMMA_3N_ENDPOINT_ID"
)
GOOGLE_CLOUD_PROJECT_NUMBER = os.environ.get(
    "GOOGLE_CLOUD_PROJECT_NUMBER", "YOUR_PROJECT_NUMBER"
)

VERTEX_URL_ENV = os.environ.get("VERTEX_ENDPOINT_URL", "")
VERTEX_URL = (
    VERTEX_URL_ENV
    if VERTEX_URL_ENV
    else (
        f"https://{VERTEX_ENDPOINT_ID}.{GOOGLE_CLOUD_REGION}-{GOOGLE_CLOUD_PROJECT_NUMBER}"
        f".prediction.vertexai.goog/v1/projects/{GOOGLE_CLOUD_PROJECT}/locations/"
        f"{GOOGLE_CLOUD_REGION}/endpoints/{VERTEX_ENDPOINT_ID}:rawPredict"
    )
)
GEMMA_3N_URL = os.environ.get("GEMMA_3N_ENDPOINT_URL", "")
EMBEDDING_MODEL = "google/embeddinggemma-2"
GEMMA_3N_MODEL = os.environ.get("GEMMA_3N_MODEL", "google/gemma-3n-E2B-it")
BUNDLED_JSON = "assets/data/bundled_memories.json"

_TOKEN_CACHE = {"token": None, "expiry": 0.0}
_RESOLVED_VERTEX_URL = None
_RESOLVED_GEMMA_3N_URL = None


def _resolve_endpoint_url(endpoint_id, token):
    """Queries Vertex AI endpoint metadata for dedicatedEndpointDns and returns the rawPredict URL."""
    ep_meta_url = (
        f"https://{GOOGLE_CLOUD_REGION}-aiplatform.googleapis.com/v1beta1/projects/"
        f"{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_REGION}/endpoints/{endpoint_id}"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": GOOGLE_CLOUD_PROJECT,
    }
    try:
        req = urllib.request.Request(ep_meta_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            meta = json.loads(resp.read().decode("utf-8"))
            dns = meta.get("dedicatedEndpointDns")
            if dns:
                return (
                    f"https://{dns}/v1/projects/{GOOGLE_CLOUD_PROJECT}/locations/"
                    f"{GOOGLE_CLOUD_REGION}/endpoints/{endpoint_id}:rawPredict"
                )
    except Exception as e:
        sys.stderr.write(f"[VertexAI] Could not resolve dedicatedEndpointDns for {endpoint_id}: {e}\n")
    return None


def get_vertex_url(token):
    """Returns the rawPredict URL for the EmbeddingGemma 2 endpoint, auto-resolving dedicatedEndpointDns if needed."""
    global VERTEX_URL, _RESOLVED_VERTEX_URL
    if VERTEX_URL_ENV:
        return VERTEX_URL_ENV
    if _RESOLVED_VERTEX_URL:
        return _RESOLVED_VERTEX_URL
    if VERTEX_ENDPOINT_ID and VERTEX_ENDPOINT_ID != "YOUR_ENDPOINT_ID":
        resolved = _resolve_endpoint_url(VERTEX_ENDPOINT_ID, token)
        if resolved:
            _RESOLVED_VERTEX_URL = resolved
            VERTEX_URL = resolved
            return resolved
    return VERTEX_URL


def get_gemma_3n_url(token):
    """Returns the rawPredict URL for the Gemma 3n endpoint, auto-resolving dedicatedEndpointDns if needed."""
    global _RESOLVED_GEMMA_3N_URL
    if GEMMA_3N_URL:
        return GEMMA_3N_URL
    if _RESOLVED_GEMMA_3N_URL:
        return _RESOLVED_GEMMA_3N_URL
    if not GEMMA_3N_ENDPOINT_ID or GEMMA_3N_ENDPOINT_ID == "YOUR_GEMMA_3N_ENDPOINT_ID":
        return (
            f"https://{GEMMA_3N_ENDPOINT_ID}.{GOOGLE_CLOUD_REGION}-{GOOGLE_CLOUD_PROJECT_NUMBER}"
            f".prediction.vertexai.goog/v1/projects/{GOOGLE_CLOUD_PROJECT}/locations/"
            f"{GOOGLE_CLOUD_REGION}/endpoints/{GEMMA_3N_ENDPOINT_ID}:rawPredict"
        )
    resolved = _resolve_endpoint_url(GEMMA_3N_ENDPOINT_ID, token)
    if resolved:
        _RESOLVED_GEMMA_3N_URL = resolved
        return resolved
    return (
        f"https://{GOOGLE_CLOUD_REGION}-aiplatform.googleapis.com/v1/projects/"
        f"{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_REGION}/endpoints/{GEMMA_3N_ENDPOINT_ID}:rawPredict"
    )


def get_token(cache_ttl_seconds=300, force_refresh=False):
    """Fetches a Google Cloud access token with in-memory TTL caching."""
    now = time.time()
    if not force_refresh and _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expiry"]:
        return _TOKEN_CACHE["token"]
    try:
        token = (
            subprocess.check_output(["gcloud", "auth", "print-access-token"])
            .decode("utf-8")
            .strip()
        )
        _TOKEN_CACHE["token"] = token
        _TOKEN_CACHE["expiry"] = now + cache_ttl_seconds
        return token
    except Exception as e:
        sys.stderr.write(f"Failed to fetch gcloud token: {e}\n")
        return None


def detect_media_type(extension):
    """Maps a file extension (with or without leading dot) to a Lark media type."""
    ext = extension.lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"]:
        return "photo"
    if ext in [".mp4", ".mov", ".m4v", ".webm", ".avi"]:
        return "video"
    if ext in [".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg"]:
        return "voiceMemo"
    return "textNote"


def make_local_file_id(file_path):
    """Generates a deterministic MD5-based ID for a local file path."""
    digest = hashlib.md5(file_path.encode("utf-8")).hexdigest()[:16]
    return f"local_{digest}"


def embed_text(text, token, task_prefix="task: search query | query: "):
    """Embeds a single text string using EmbeddingGemma 2 on Vertex AI."""
    formatted_input = f"{task_prefix}{text[:2000]}" if task_prefix else text[:2000]
    payload = json.dumps({
        "model": EMBEDDING_MODEL,
        "input": [formatted_input],
    }).encode("utf-8")

    endpoint_url = get_vertex_url(token)
    for attempt in range(1, 61):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        try:
            req = urllib.request.Request(endpoint_url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["data"][0]["embedding"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code == 401 and attempt < 5:
                fresh = get_token(force_refresh=True)
                if fresh:
                    token = fresh
                    continue
            if e.code == 429 and attempt < 60:
                sys.stderr.write(
                    f"[EmbeddingGemma2] [{attempt}/60] Endpoint scaling up from zero "
                    f"(HTTP 429)... waiting 5s\n"
                )
                time.sleep(5)
            else:
                sys.stderr.write(f"Embedding HTTPError {e.code}: {body}\n")
                return None
        except Exception as e:
            sys.stderr.write(f"Embedding error: {e}\n")
            return None
    return None


def fetch_embeddings_batch(texts, token, max_retries=60, retry_delay=5):
    """Fetches embeddings for a batch of input strings with HTTP 429 retry logic."""
    payload = json.dumps({
        "model": EMBEDDING_MODEL,
        "input": texts,
    }).encode("utf-8")

    endpoint_url = get_vertex_url(token)
    for attempt in range(1, max_retries + 1):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        try:
            req = urllib.request.Request(endpoint_url, data=payload, headers=headers)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [item["embedding"] for item in data["data"]]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code == 401 and attempt < 5:
                fresh = get_token(force_refresh=True)
                if fresh:
                    token = fresh
                    continue
            if e.code == 429 and attempt < max_retries:
                print(
                    f"[{attempt}/{max_retries}] Endpoint scaling up from zero "
                    f"(HTTP 429)... waiting {retry_delay}s: {body}"
                )
                time.sleep(retry_delay)
            else:
                print(f"HTTPError {e.code}: {body}")
                raise
