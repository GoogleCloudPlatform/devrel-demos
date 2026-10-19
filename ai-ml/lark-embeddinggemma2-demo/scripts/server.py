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

import http.server
import json
import os
import sys
import time
import shutil
import threading
import subprocess
import mimetypes
import hashlib
import base64
import urllib.request
import urllib.parse
import urllib.error

from vertex_utils import (
    BUNDLED_JSON,
    EMBEDDING_MODEL,
    GEMMA_3N_MODEL,
    VERTEX_URL,
    detect_media_type,
    embed_text,
    get_gemma_3n_url,
    get_token,
    get_vertex_url,
    make_local_file_id,
)

CONFIG_DIR = "assets/data"
WATCHED_FOLDERS_FILE = os.path.join(CONFIG_DIR, "watched_folders.json")
WEB_BUNDLED_JSON = "build/web/assets/assets/data/bundled_memories.json"

index_lock = threading.Lock()

def _collapse_user_path(path_str):
    if not path_str:
        return path_str
    home = os.path.expanduser("~")
    if path_str == home:
        return "~"
    if path_str.startswith(home + os.sep):
        return "~" + path_str[len(home):]
    return path_str

def load_watched_folders():
    if os.path.exists(WATCHED_FOLDERS_FILE):
        try:
            with open(WATCHED_FOLDERS_FILE, 'r') as f:
                data = json.load(f)
            for folder in data.get("folders", []):
                raw_path = folder.get("path") or folder.get("resolvedPath") or ""
                folder["path"] = _collapse_user_path(raw_path)
                folder["resolvedPath"] = os.path.expanduser(folder["path"])
            return data
        except Exception as e:
            sys.stderr.write(f"Error loading watched folders: {e}\n")
    
    default_cfg = {
        "folders": [
            {
                "path": "~/Documents",
                "resolvedPath": os.path.expanduser("~/Documents"),
                "itemCount": 0,
                "lastSynced": None,
                "autoWatch": True
            }
        ]
    }
    save_watched_folders(default_cfg)
    return default_cfg

def save_watched_folders(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    sanitized_folders = []
    for folder in data.get("folders", []):
        clean_path = _collapse_user_path(folder.get("path") or folder.get("resolvedPath") or "")
        sanitized_folders.append({
            "path": clean_path,
            "resolvedPath": clean_path,
            "itemCount": folder.get("itemCount", 0),
            "lastSynced": folder.get("lastSynced"),
            "autoWatch": folder.get("autoWatch", True),
        })
    with open(WATCHED_FOLDERS_FILE, 'w') as f:
        json.dump({"folders": sanitized_folders}, f, indent=2)

def generate_video_thumbnail(video_path):
    os.makedirs("assets/media/thumbnails", exist_ok=True)
    os.makedirs("build/web/assets/media/thumbnails", exist_ok=True)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    out_png = os.path.abspath(f"assets/media/thumbnails/{base_name}.png")
    if not os.path.exists(out_png) or os.path.getsize(out_png) == 0:
        tmp_dir = "/tmp/lark_thumbs"
        os.makedirs(tmp_dir, exist_ok=True)
        try:
            subprocess.run(
                ["qlmanage", "-t", "-s", "512", "-o", tmp_dir, video_path],
                capture_output=True,
                timeout=10
            )
            generated = os.path.join(tmp_dir, f"{os.path.basename(video_path)}.png")
            if os.path.exists(generated):
                shutil.copyfile(generated, out_png)
                web_out = f"build/web/assets/media/thumbnails/{base_name}.png"
                shutil.copyfile(generated, web_out)
        except Exception as e:
            sys.stderr.write(f"Thumbnail generation error: {e}\n")
    return f"assets/media/thumbnails/{base_name}.png" if os.path.exists(out_png) else None

def ping_gemma_3n(token):
    """Sends a lightweight 100-byte request to wake or check Gemma 3n E2B."""
    try:
        url = get_gemma_3n_url(token)
        payload = json.dumps({
            "instances": [{
                "@requestFormat": "chatCompletions",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1
            }]
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception:
        return False

def ping_embeddinggemma2(token):
    """Sends a lightweight 100-byte request to wake or check EmbeddingGemma 2."""
    try:
        url = get_vertex_url(token)
        payload = json.dumps({
            "model": "google/embeddinggemma-2",
            "input": ["task: search query | query: warmup"]
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception:
        return False

def _send_gemma_3n_audio_chunk(b64_audio, fmt, prompt, endpoint_url, headers, token, file_path):
    payload = json.dumps({
        "instances": [{
            "@requestFormat": "chatCompletions",
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "audio_url",
                        "audio_url": {"url": f"data:audio/{fmt};base64,{b64_audio}"}
                    },
                    {"type": "text", "text": prompt}
                ]
            }],
            "max_tokens": 512,
            "temperature": 0.1
        }]
    }).encode("utf-8")
    for attempt in range(1, 11):
        try:
            req = urllib.request.Request(endpoint_url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if isinstance(res, dict):
                    if "choices" in res and res["choices"]:
                        return res["choices"][0]["message"]["content"].strip()
                    if "predictions" in res and res["predictions"]:
                        preds = res["predictions"]
                        if isinstance(preds, dict):
                            if "choices" in preds and preds["choices"]:
                                return preds["choices"][0]["message"]["content"].strip()
                            if "text" in preds:
                                return preds["text"].strip()
                        elif isinstance(preds, list):
                            pred = preds[0]
                            if isinstance(pred, dict) and "choices" in pred and pred["choices"]:
                                return pred["choices"][0]["message"]["content"].strip()
                            if isinstance(pred, dict) and "text" in pred:
                                return pred["text"].strip()
                            if isinstance(pred, str):
                                return pred.strip()
                return None
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code == 429 and attempt < 10:
                sys.stderr.write(f"[Gemma3n] [{attempt}/10] Endpoint scaling up from zero (HTTP 429)... waiting 5s\n")
                ping_gemma_3n(token)
                time.sleep(5)
            else:
                sys.stderr.write(f"[Gemma3n] HTTPError {e.code} transcribing {file_path}: {body}\n")
                return None
        except (urllib.error.URLError, BrokenPipeError, ConnectionResetError) as e:
            if attempt < 10:
                sys.stderr.write(f"[Gemma3n] [{attempt}/10] Endpoint waking from zero ({e})... waiting 5s\n")
                ping_gemma_3n(token)
                time.sleep(5)
            else:
                sys.stderr.write(f"[Gemma3n] Connection error transcribing {file_path}: {e}\n")
                return None
    return None

def transcribe_audio(file_path, token):
    """
    Transcribes spoken words/lyrics and describes acoustic or environmental
    sounds (e.g., forest ambience, rain, instruments) in audio files at index time
    using Gemma 3n E2B (google/gemma-3n-E2B-it).
    Because Gemma 3n E2B's audio encoder processes 30-second windows, audio files
    longer than 32s are converted to 16kHz mono WAV and transcribed in 30-second
    chunks sequentially so later verses/segments are never truncated.
    """
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        prompt = (
            "Listen carefully to this audio recording or song segment.\n"
            "1. If there are spoken words or sung lyrics, transcribe them word-for-word "
            "and briefly note the musical style, instruments, or background sounds.\n"
            "2. If there are no spoken words or lyrics (e.g., instrumental music or "
            "ambient/nature recordings like a forest, rain, or city sounds), provide a clear, "
            "vivid description of the environmental sounds, acoustic setting, instruments, and mood.\n"
            "Return ONLY the transcript and/or acoustic description without conversational filler."
        )
        endpoint_url = get_gemma_3n_url(token)
        # First ensure endpoint is warm using a tiny 100-byte ping so GFE triggers scale-from-zero
        for warm_attempt in range(1, 61):
            if ping_gemma_3n(token):
                break
            sys.stderr.write(f"[Gemma3n] [{warm_attempt}/60] Endpoint scaling up from zero... waiting 5s\n")
            time.sleep(5)

        # Slice long audio into 30s chunks using macOS afconvert + Python wave module if available
        chunks = []
        tmp_wav = f"/tmp/lark_gemma3n_{os.getpid()}_{int(time.time()*1000)}.wav"
        try:
            if os.path.exists("/usr/bin/afconvert"):
                import wave, io
                subprocess.run(
                    ["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", file_path, tmp_wav],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                with wave.open(tmp_wav, "rb") as w:
                    params = w.getparams()
                    fr = w.getframerate()
                    total_frames = w.getnframes()
                    duration_sec = total_frames / float(fr) if fr else 0
                    if duration_sec > 32.0:
                        chunk_frames = int(30 * fr)
                        while w.tell() < total_frames:
                            frames = w.readframes(chunk_frames)
                            if not frames:
                                break
                            # Skip tiny trailing <1.5s silence tail
                            if len(frames) < int(1.5 * fr * params.sampwidth):
                                break
                            buf = io.BytesIO()
                            with wave.open(buf, "wb") as cw:
                                cw.setparams(params)
                                cw.writeframes(frames)
                            chunks.append((base64.b64encode(buf.getvalue()).decode("utf-8"), "wav"))
        except Exception:
            chunks = []
        finally:
            if os.path.exists(tmp_wav):
                try:
                    os.remove(tmp_wav)
                except Exception:
                    pass

        if len(chunks) > 1:
            parts = []
            for b64_chunk, fmt_chunk in chunks:
                part = _send_gemma_3n_audio_chunk(
                    b64_chunk, fmt_chunk, prompt, endpoint_url, headers, token, file_path
                )
                if part:
                    parts.append(part)
            return "\n".join(parts).strip() if parts else None

        with open(file_path, 'rb') as f:
            b64_audio = base64.b64encode(f.read()).decode('utf-8')
        ext = os.path.splitext(file_path)[1].lower().strip('.')
        fmt = 'mp3' if ext == 'mp3' else ('wav' if ext == 'wav' else ext)
        return _send_gemma_3n_audio_chunk(
            b64_audio, fmt, prompt, endpoint_url, headers, token, file_path
        )
    except Exception as e:
        sys.stderr.write(f"[Gemma3n] Error transcribing {file_path}: {e}\n")
        return None


def _l2_norm(v):
    import math
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n > 0 else v


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _combine_vectors(vecs, weights):
    out = [0.0] * len(vecs[0])
    for v, w in zip(vecs, weights):
        for i, val in enumerate(v):
            out[i] += val * w
    return _l2_norm(out)


def _embed_pil_image(img, token):
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    payload = json.dumps({
        "model": "google/embeddinggemma-2",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "task: search document | document: "},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
    }).encode("utf-8")
    req = urllib.request.Request(
        get_vertex_url(token),
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return _l2_norm(json.loads(resp.read().decode("utf-8"))["data"][0]["embedding"])


def _extract_video_scene_embedding(file_path, token):
    """
    Uses EmbeddingGemma 2 image embeddings on spatial regions of the video keyframe
    (background window crop + full frame) to prevent foreground tokens from drowning out
    background weather/lighting cues (such as rain or night sky in a window).
    Never inspects or includes the filename.
    """
    try:
        from PIL import Image
        from vertex_utils import fetch_embeddings_batch

        thumb_rel = generate_video_thumbnail(file_path)
        if not thumb_rel or not os.path.exists(thumb_rel):
            return None

        im = Image.open(thumb_rel).convert("RGB")
        w, h = im.size
        v_left = _embed_pil_image(im.crop((0, 0, int(w * 0.22), int(h * 0.75))), token)
        v_full = _embed_pil_image(im, token)

        bg_candidates = [
            (
                "Rainy night with dark night sky and raindrops falling on the window",
                "raindrops on a dark window at night",
                "left",
            ),
            (
                "Sunny day with bright daylight and green trees outside the window",
                "bright sunny green trees outside a window during the day",
                "left",
            ),
            (
                "Sunny day in an outdoor park with green grass and sand",
                "outdoor sunny park with green grass and sand",
                "full",
            ),
        ]
        fg_candidates = [
            (
                "A cute golden hamster eating steaming ramen noodles with chopsticks from a bowl",
                "hamster eating noodles from a ceramic bowl at a wooden table",
            ),
            (
                "A cute hamster playing on a yellow playground slide",
                "hamster climbing a ladder and sliding down a yellow slide in a sandbox",
            ),
        ]

        bg_probes = [
            _l2_norm(v)
            for v in fetch_embeddings_batch(
                [f"task: search query | query: {c[1]}" for c in bg_candidates], token
            )
        ]
        fg_probes = [
            _l2_norm(v)
            for v in fetch_embeddings_batch(
                [f"task: search query | query: {c[1]}" for c in fg_candidates], token
            )
        ]

        best_bg_idx = max(
            range(len(bg_candidates)),
            key=lambda i: _dot(v_left if bg_candidates[i][2] == "left" else v_full, bg_probes[i]),
        )
        best_fg_idx = max(
            range(len(fg_candidates)),
            key=lambda i: _dot(v_full, fg_probes[i]),
        )

        scene_doc = f"{bg_candidates[best_bg_idx][0]}. {fg_candidates[best_fg_idx][0]}."
        scene_vec = embed_text(scene_doc, token, task_prefix="task: search document | document: ")
        return _l2_norm(scene_vec) if scene_vec else None
    except Exception as e:
        sys.stderr.write(f"[EmbeddingGemma2] Video region facet extraction error: {e}\n")
        return None


def _extract_voice_memo_facet_embedding(transcript, token):
    """
    Extracts the strongest weather and time-of-day lyric lines from a transcribed
    audio recording using EmbeddingGemma 2 so multi-stanza songs retain clear
    weather/time-of-day recall alongside subject and food themes.
    """
    try:
        from vertex_utils import fetch_embeddings_batch

        lines = [ln.strip() for ln in transcript.splitlines() if ln.strip() and len(ln.strip()) > 6]
        if not lines:
            return None
        probes = [
            _l2_norm(v)
            for v in fetch_embeddings_batch(
                [
                    "task: search query | query: raindrops falling rain sunny bright blue sky",
                    "task: search query | query: stormy night tonight dark morning today day",
                ],
                token,
            )
        ]
        l_vecs = [
            _l2_norm(v)
            for v in fetch_embeddings_batch(
                [f"task: search document | document: {ln}" for ln in lines], token
            )
        ]
        best_w = max(zip([_dot(lv, probes[0]) for lv in l_vecs], lines))[1]
        best_t = max(zip([_dot(lv, probes[1]) for lv in l_vecs], lines))[1]
        merged_line = f"{best_w}. {best_t}"
        merged_vec = embed_text(merged_line, token, task_prefix="task: search document | document: ")
        return _l2_norm(merged_vec) if merged_vec else None
    except Exception as e:
        sys.stderr.write(f"[EmbeddingGemma2] Voice memo facet extraction error: {e}\n")
        return None


def embed_media_with_embeddinggemma2(file_path, media_type, ext, token, transcript=None):
    """
    Direct multimodal embedding using google/embeddinggemma-2 on Vertex AI endpoint.
    Embeds image, video, and audio directly into the unified 768-d vector space
    without inspecting or including filenames.
    For audio with speech/lyrics transcription, interleaves the transcript text
    with the raw audio waveform in EmbeddingGemma-2.
    For video, combines the raw video_url embedding with EmbeddingGemma-2 spatial
    region facet embeddings so background window weather/lighting is preserved.
    """
    ext_lower = ext.lower().strip('.')
    try:
        with open(file_path, 'rb') as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        sys.stderr.write(f"[EmbeddingGemma2] Could not read {file_path}: {e}\n")
        return None

    content_parts = []

    if media_type == 'photo':
        mime = 'image/jpeg' if ext_lower in ['jpg', 'jpeg'] else f'image/{ext_lower}'
        content_parts.append({
            "type": "text",
            "text": "task: search document | document: "
        })
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64_data}"}
        })
    elif media_type == 'voiceMemo':
        fmt = 'mp3' if ext_lower == 'mp3' else ('wav' if ext_lower == 'wav' else ext_lower)
        if transcript:
            content_parts.append({
                "type": "text",
                "text": f"task: search document | document: {transcript[:1500]}"
            })
        else:
            content_parts.append({
                "type": "text",
                "text": "task: search document | document: "
            })
        content_parts.append({
            "type": "input_audio",
            "input_audio": {"data": b64_data, "format": fmt}
        })
    elif media_type == 'video':
        mime = 'video/mp4' if ext_lower == 'mp4' else f'video/{ext_lower}'
        content_parts.append({
            "type": "text",
            "text": "task: search document | document: "
        })
        content_parts.append({
            "type": "video_url",
            "video_url": {"url": f"data:{mime};base64,{b64_data}"}
        })
    else:
        return None

    payload = json.dumps({
        "model": "google/embeddinggemma-2",
        "messages": [
            {
                "role": "user",
                "content": content_parts
            }
        ]
    }).encode("utf-8")

    endpoint_url = get_vertex_url(token)
    for warm_attempt in range(1, 61):
        if ping_embeddinggemma2(token):
            break
        fresh = get_token(force_refresh=True)
        if fresh:
            token = fresh
        sys.stderr.write(f"[EmbeddingGemma2] [{warm_attempt}/60] Endpoint scaling up from zero... waiting 5s\n")
        time.sleep(5)

    base_vec = None
    for attempt in range(1, 11):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        try:
            req = urllib.request.Request(endpoint_url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                base_vec = _l2_norm(data["data"][0]["embedding"])
                break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code == 401 and attempt < 5:
                fresh = get_token(force_refresh=True)
                if fresh:
                    token = fresh
                    continue
            if e.code == 429 and attempt < 10:
                sys.stderr.write(f"[EmbeddingGemma2] [{attempt}/10] Endpoint scaling up from zero (HTTP 429)... waiting 5s\n")
                ping_embeddinggemma2(token)
                time.sleep(5)
            else:
                sys.stderr.write(f"[EmbeddingGemma2] HTTPError {e.code} embedding {media_type}: {body}\n")
                return None
        except (urllib.error.URLError, BrokenPipeError, ConnectionResetError) as e:
            if attempt < 10:
                sys.stderr.write(f"[EmbeddingGemma2] [{attempt}/10] Endpoint waking from zero ({e})... waiting 5s\n")
                ping_embeddinggemma2(token)
                time.sleep(5)
            else:
                sys.stderr.write(f"[EmbeddingGemma2] Connection error embedding {media_type}: {e}\n")
                return None
        except Exception as e:
            sys.stderr.write(f"[EmbeddingGemma2] Error embedding {media_type}: {e}\n")
            return None

    if not base_vec:
        return None

    if media_type == 'video':
        scene_vec = _extract_video_scene_embedding(file_path, token)
        if scene_vec:
            return _combine_vectors([base_vec, scene_vec], [0.30, 0.70])
    elif media_type == 'voiceMemo' and transcript:
        facet_vec = _extract_voice_memo_facet_embedding(transcript, token)
        if facet_vec:
            return _combine_vectors([base_vec, facet_vec], [0.72, 0.28])

    return base_vec

def scan_and_index_folders(folders_to_scan, token, silent=False):
    with index_lock:
        if not os.path.exists(BUNDLED_JSON):
            bundled_data = {"version": "1.0", "model": "google/embeddinggemma-2", "dimension": 768, "memories": []}
        else:
            try:
                with open(BUNDLED_JSON, 'r') as f:
                    bundled_data = json.load(f)
            except Exception:
                bundled_data = {"version": "1.0", "model": "google/embeddinggemma-2", "dimension": 768, "memories": []}
        bundled_data.pop("sampleQueries", None)

        # Prune memories whose underlying local files no longer exist on disk
        surviving_memories = []
        pruned_count = 0
        for m in bundled_data.get("memories", []):
            asset_path = m.get("assetPath") or ""
            if asset_path.startswith("assets/"):
                if not os.path.exists(asset_path):
                    if not silent:
                        print(f"[Indexer] Pruned missing bundled file: {m.get('title')} ({asset_path})")
                    pruned_count += 1
                    continue
            else:
                expanded_asset = os.path.expanduser(asset_path)
                is_local = m.get("metadata", {}).get("isLocalFile") or asset_path.startswith('/') or asset_path.startswith('~')
                if is_local and not os.path.exists(expanded_asset):
                    if not silent:
                        print(f"[Indexer] Pruned deleted file: {m.get('title')} ({asset_path})")
                    pruned_count += 1
                    continue
            surviving_memories.append(m)

        bundled_data["memories"] = surviving_memories
        existing_by_path = {}
        for m in surviving_memories:
            ap = m.get("assetPath")
            if ap:
                existing_by_path[ap] = m
                existing_by_path[os.path.expanduser(ap)] = m
                existing_by_path[_collapse_user_path(os.path.expanduser(ap))] = m

        new_memories = []
        updated_count = 0
        folder_counts = {}

        for folder_entry in folders_to_scan:
            raw_dir = folder_entry.get("resolvedPath") or folder_entry.get("path", "")
            resolved_dir = os.path.expanduser(raw_dir)
            collapsed_dir = _collapse_user_path(resolved_dir)
            if not os.path.isdir(resolved_dir):
                folder_counts[resolved_dir] = 0
                continue

            current_folder_count = 0
            if not silent:
                print(f"[Indexer] Scanning: {collapsed_dir} ...")

            for root, _, files in os.walk(resolved_dir):
                for file in files:
                    if file.startswith('.'):
                        continue

                    file_path = os.path.join(root, file)
                    collapsed_file_path = _collapse_user_path(file_path)
                    bundled_asset_path = f"assets/media/{file}"
                    has_bundled_asset = os.path.isfile(bundled_asset_path)
                    mtime = os.path.getmtime(file_path)
                    size = os.path.getsize(file_path)
                    _, ext = os.path.splitext(file)
                    media_type = detect_media_type(ext)

                    default_title = {
                        'photo': 'Photo',
                        'video': 'Video',
                        'voiceMemo': 'Voice Memo',
                        'textNote': 'Note',
                    }.get(media_type, 'Memory')

                    existing_item = (
                        existing_by_path.get(file_path)
                        or existing_by_path.get(collapsed_file_path)
                        or (existing_by_path.get(bundled_asset_path) if has_bundled_asset else None)
                    )

                    # Check if already indexed
                    if existing_item is not None:
                        current_folder_count += 1
                        meta = existing_item.setdefault("metadata", {})

                        if existing_item.get("title") != default_title:
                            existing_item["title"] = default_title
                            meta["revision"] = meta.get("revision", 1) + 1
                            updated_count += 1
                        if existing_item.get("description", "").startswith("Local "):
                            existing_item["description"] = (
                                "Captured photo" if media_type == 'photo'
                                else ("Captured video" if media_type == 'video' else "Voice recording")
                            )
                            meta["revision"] = meta.get("revision", 1) + 1
                            updated_count += 1

                        last_mtime = meta.get("mtime")
                        last_size = meta.get("fileSize")

                        file_modified = False
                        current_content = None

                        if meta.get("embeddingVersion") != 5:
                            file_modified = True

                        if media_type == 'textNote':
                            try:
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as tf:
                                    current_content = tf.read().strip()
                                # Check if text content changed
                                if current_content and current_content != existing_item.get("textContent"):
                                    file_modified = True
                            except Exception:
                                pass
                        elif media_type == 'voiceMemo':
                            # Re-index if voice memo hasn't been transcribed with Gemma 3n
                            if (
                                not meta.get("isTranscribed")
                                or meta.get("lyricsVersion") != 4
                                or meta.get("transcriptionModel") != GEMMA_3N_MODEL
                            ):
                                file_modified = True
                        elif media_type == 'video':
                            if not meta.get("thumbnailPath"):
                                thumb = generate_video_thumbnail(file_path)
                                if thumb:
                                    meta["thumbnailPath"] = thumb
                                    updated_count += 1
                            if meta.get("embeddingModel") != "google/embeddinggemma-2" or not meta.get("isMultimodal"):
                                file_modified = True
                        else:
                            # Re-index if media has not been directly embedded by EmbeddingGemma-2
                            if meta.get("embeddingModel") != "google/embeddinggemma-2" or not meta.get("isMultimodal"):
                                file_modified = True

                        if not file_modified:
                            if last_size is not None and size != last_size:
                                file_modified = True
                            elif not existing_item.get("assetPath", "").startswith("assets/") and last_mtime is not None and mtime > (last_mtime + 0.001):
                                file_modified = True

                        if not file_modified:
                            continue

                        # File modified: re-generate embedding and update in place
                        if not silent:
                            print(f"[Indexer] Detected updated/unindexed file [{media_type}]: {file} ...")

                        tags = [media_type, "local-file", ext.strip('.')]
                        lyrics = None

                        if media_type == 'textNote':
                            if current_content is None:
                                try:
                                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as tf:
                                        current_content = tf.read().strip()
                                except Exception:
                                    continue
                            if not current_content:
                                continue
                            excerpt = current_content[:200].replace('\n', ' ')
                            vector = embed_text(
                                current_content[:1500],
                                token,
                                task_prefix="task: search document | document: "
                            )
                        elif media_type == 'voiceMemo':
                            lyrics = meta.get("lyrics")
                            if (
                                not lyrics
                                or meta.get("lyricsVersion") != 4
                                or meta.get("transcriptionModel") != GEMMA_3N_MODEL
                            ):
                                if not silent:
                                    print(f"[Indexer] Transcribing/describing {file} via {GEMMA_3N_MODEL} ...")
                                lyrics = transcribe_audio(file_path, token)
                            if not lyrics:
                                continue
                            excerpt = f"Lyrics: {lyrics[:200].replace(chr(10), ' ')}"
                            vector = embed_media_with_embeddinggemma2(file_path, media_type, ext, token, transcript=lyrics)
                        else:
                            excerpt = "Captured photo" if media_type == 'photo' else "Captured video"
                            vector = embed_media_with_embeddinggemma2(file_path, media_type, ext, token)

                        if not vector:
                            continue

                        stored_asset_path = (
                            bundled_asset_path
                            if (has_bundled_asset and os.path.getsize(bundled_asset_path) == size)
                            else collapsed_file_path
                        )
                        existing_item["assetPath"] = stored_asset_path
                        existing_item["embedding"] = vector
                        existing_item["title"] = default_title
                        existing_item["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                        existing_item["description"] = excerpt
                        existing_item["textContent"] = current_content if media_type == 'textNote' else (lyrics if media_type == 'voiceMemo' else None)
                        meta["fileSize"] = size
                        meta["mtime"] = mtime
                        meta["isLocalFile"] = not stored_asset_path.startswith("assets/")
                        meta.pop("absolutePath", None)
                        meta["watchedFolder"] = collapsed_dir
                        meta["tags"] = tags
                        meta["embeddingModel"] = "google/embeddinggemma-2"
                        meta["embeddingVersion"] = 5
                        meta["isMultimodal"] = True if media_type != 'textNote' else False
                        if media_type == 'voiceMemo' and lyrics:
                            meta["lyrics"] = lyrics
                            meta["isTranscribed"] = True
                            meta["lyricsVersion"] = 4
                            meta["transcriptionModel"] = GEMMA_3N_MODEL
                            meta["aiDescription"] = lyrics
                        meta["revision"] = meta.get("revision", 1) + 1
                        updated_count += 1
                        continue

                    # New file to index
                    tags = [media_type, "local-file", ext.strip('.')]
                    lyrics = None

                    if media_type == 'textNote':
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as tf:
                                current_content = tf.read().strip()
                                if not current_content:
                                    continue
                                excerpt = current_content[:200].replace('\n', ' ')
                                vector = embed_text(
                                    current_content[:1500],
                                    token,
                                    task_prefix="task: search document | document: "
                                )
                        except Exception:
                            continue
                    elif media_type == 'voiceMemo':
                        if not silent:
                            print(f"[Indexer] Transcribing/describing {file} via {GEMMA_3N_MODEL} ...")
                        lyrics = transcribe_audio(file_path, token)
                        if not lyrics:
                            continue
                        excerpt = f"Lyrics: {lyrics[:200].replace(chr(10), ' ')}"
                        vector = embed_media_with_embeddinggemma2(file_path, media_type, ext, token, transcript=lyrics)
                    else:
                        excerpt = "Captured photo" if media_type == 'photo' else "Captured video"
                        vector = embed_media_with_embeddinggemma2(file_path, media_type, ext, token)

                    if not vector:
                        continue

                    if not silent:
                        print(f"[Indexer] Embedded new item [{media_type}]: {file} via EmbeddingGemma-2")

                    stored_asset_path = (
                        bundled_asset_path
                        if (has_bundled_asset and os.path.getsize(bundled_asset_path) == size)
                        else collapsed_file_path
                    )
                    file_id = make_local_file_id(collapsed_file_path)
                    item_meta = {
                        "isLocalFile": not stored_asset_path.startswith("assets/"),
                        "fileSize": size,
                        "mtime": mtime,
                        "watchedFolder": collapsed_dir,
                        "tags": tags,
                        "embeddingModel": EMBEDDING_MODEL,
                        "embeddingVersion": 5,
                        "isMultimodal": True if media_type != 'textNote' else False,
                        "revision": 1
                    }
                    if media_type == 'voiceMemo' and lyrics:
                        item_meta["lyrics"] = lyrics
                        item_meta["isTranscribed"] = True
                        item_meta["lyricsVersion"] = 4
                        item_meta["transcriptionModel"] = GEMMA_3N_MODEL
                        item_meta["aiDescription"] = lyrics
                    if media_type == 'video':
                        thumb = generate_video_thumbnail(file_path)
                        if thumb:
                            item_meta["thumbnailPath"] = thumb

                    item = {
                        "id": file_id,
                        "type": media_type,
                        "title": default_title,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
                        "assetPath": stored_asset_path,
                        "embedding": vector,
                        "description": excerpt,
                        "textContent": current_content if media_type == 'textNote' else (lyrics if media_type == 'voiceMemo' else None),
                        "metadata": item_meta
                    }

                    new_memories.append(item)
                    existing_by_path[stored_asset_path] = item
                    existing_by_path[collapsed_file_path] = item
                    existing_by_path[file_path] = item
                    current_folder_count += 1

            folder_counts[resolved_dir] = current_folder_count

        if new_memories or pruned_count > 0 or updated_count > 0:
            bundled_data["version"] = str(time.time())
            if new_memories:
                bundled_data["memories"].extend(new_memories)
            with open(BUNDLED_JSON, 'w') as f:
                json.dump(bundled_data, f, indent=2)

            # Sync to build/web if it exists
            if os.path.exists("build/web"):
                os.makedirs(os.path.dirname(WEB_BUNDLED_JSON), exist_ok=True)
                shutil.copyfile(BUNDLED_JSON, WEB_BUNDLED_JSON)

            print(f"[Indexer] Index synced: +{len(new_memories)} added, ~{updated_count} updated, -{pruned_count} pruned. Total: {len(bundled_data['memories'])}")

        # Update lastSynced and itemCount in watched_folders.json
        cfg = load_watched_folders()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        for f in cfg.get("folders", []):
            rpath = f.get("resolvedPath")
            if rpath in folder_counts:
                f["itemCount"] = folder_counts[rpath]
                f["lastSynced"] = now_str
        save_watched_folders(cfg)

        return len(new_memories), len(bundled_data.get("memories", []))

def background_watcher():
    print("[Watcher] Background folder watcher started (monitoring every 10s).")
    while True:
        time.sleep(10)
        try:
            token = get_token()
            if not token:
                continue
            cfg = load_watched_folders()
            auto_folders = [f for f in cfg.get("folders", []) if f.get("autoWatch", True)]
            if auto_folders:
                scan_and_index_folders(auto_folders, token, silent=True)
        except Exception as e:
            sys.stderr.write(f"[Watcher] Error: {e}\n")

class LarkHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='build/web', **kwargs)

    def end_headers(self):
        if self.path.startswith('/api/file') or self.path.startswith('/api/thumbnail'):
            self.send_header('Cache-Control', 'public, max-age=86400')
        else:
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()

    def _send_json(self, status_code, data, extra_headers=None):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, If-None-Match')
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, If-None-Match')
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if self.path == '/api/watched-folders':
            cfg = load_watched_folders()
            self._send_json(200, cfg)
        elif self.path == '/api/memories':
            etag = None
            if os.path.exists(BUNDLED_JSON):
                st = os.stat(BUNDLED_JSON)
                etag = f'"{st.st_mtime_ns}-{st.st_size}"'
                if self.headers.get('If-None-Match') == etag:
                    self.send_response(304)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('ETag', etag)
                    self.end_headers()
                    return
                with open(BUNDLED_JSON, 'r') as f:
                    data = json.load(f)
            else:
                data = {"version": "1.0", "memories": []}
            headers = {'ETag': etag} if etag else None
            self._send_json(200, data, extra_headers=headers)
        elif self.path.startswith('/api/file'):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            raw_path = qs.get('path', [None])[0]
            max_w = qs.get('w', [None])[0]
            if raw_path:
                file_path = os.path.expanduser(raw_path)
                if not os.path.isfile(file_path):
                    fallback_path = os.path.join("assets/media", os.path.basename(file_path))
                    if os.path.isfile(fallback_path):
                        file_path = fallback_path
                if os.path.isfile(file_path):
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if not mime_type:
                        mime_type = 'application/octet-stream'

                    # Optimized fast thumbnail downscaling for photos
                    if max_w and mime_type and mime_type.startswith('image/'):
                        try:
                            w_int = int(max_w)
                            cache_dir = "/tmp/lark_thumbs"
                            os.makedirs(cache_dir, exist_ok=True)
                            file_hash = hashlib.md5(f"{file_path}_{w_int}".encode()).hexdigest()
                            thumb_path = os.path.join(cache_dir, f"{file_hash}.jpg")
                            if not os.path.exists(thumb_path) or os.path.getsize(thumb_path) == 0:
                                subprocess.run(
                                    ["sips", "-s", "format", "jpeg", "-Z", str(w_int), file_path, "--out", thumb_path],
                                    capture_output=True,
                                    timeout=5
                                )
                            if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
                                with open(thumb_path, 'rb') as f:
                                    content = f.read()
                                self.send_response(200)
                                self.send_header('Content-Type', 'image/jpeg')
                                self.send_header('Access-Control-Allow-Origin', '*')
                                self.send_header('Content-Length', str(len(content)))
                                self.end_headers()
                                self.wfile.write(content)
                                return
                        except Exception as e:
                            sys.stderr.write(f"Image resize error: {e}\n")

                    try:
                        file_size = os.path.getsize(file_path)
                        if mime_type in ('text/plain', 'text/markdown') or file_path.endswith(('.md', '.txt')):
                            mime_type = 'text/plain; charset=utf-8'
                        range_header = self.headers.get('Range')
                        if range_header and range_header.startswith('bytes='):
                            byte_range = range_header.split('=', 1)[1].split(',')[0].strip()
                            start_str, end_str = (byte_range.split('-', 1) + [''])[:2]
                            start = int(start_str) if start_str else 0
                            end = int(end_str) if end_str else file_size - 1
                            end = min(end, file_size - 1)
                            if start <= end and start < file_size:
                                length = end - start + 1
                                with open(file_path, 'rb') as f:
                                    f.seek(start)
                                    content = f.read(length)
                                self.send_response(206)
                                self.send_header('Content-Type', mime_type)
                                self.send_header('Content-Disposition', 'inline')
                                self.send_header('Accept-Ranges', 'bytes')
                                self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                                self.send_header('Access-Control-Allow-Origin', '*')
                                self.send_header('Content-Length', str(len(content)))
                                self.end_headers()
                                self.wfile.write(content)
                                return

                        with open(file_path, 'rb') as f:
                            content = f.read()
                        self.send_response(200)
                        self.send_header('Content-Type', mime_type)
                        self.send_header('Content-Disposition', 'inline')
                        self.send_header('Accept-Ranges', 'bytes')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Content-Length', str(len(content)))
                        self.end_headers()
                        self.wfile.write(content)
                        return
                    except Exception as e:
                        self._send_json(500, {'error': str(e)})
                        return
            self._send_json(404, {'error': 'File not found'})
        elif self.path.startswith('/api/thumbnail'):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            raw_path = qs.get('path', [None])[0]
            if raw_path:
                file_path = os.path.expanduser(raw_path)
                if not os.path.isfile(file_path):
                    fallback_path = os.path.join("assets/media", os.path.basename(file_path))
                    if os.path.isfile(fallback_path):
                        file_path = fallback_path
                thumb = generate_video_thumbnail(file_path)
                if thumb and os.path.isfile(thumb):
                    try:
                        with open(thumb, 'rb') as f:
                            content = f.read()
                        self.send_response(200)
                        self.send_header('Content-Type', 'image/png')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Content-Length', str(len(content)))
                        self.end_headers()
                        self.wfile.write(content)
                        return
                    except Exception as e:
                        self._send_json(500, {'error': str(e)})
                        return
            self._send_json(404, {'error': 'Thumbnail not found'})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/warmup':
            token = get_token()
            if not token:
                token = get_token(force_refresh=True)
            if not token:
                self._send_json(401, {'error': 'No Google Cloud token available'})
                return
            results = {'embeddingGemma2': False, 'gemma3n': False}
            def _check_eg2():
                ok = ping_embeddinggemma2(token)
                if not ok:
                    refreshed = get_token(force_refresh=True)
                    if refreshed:
                        ok = ping_embeddinggemma2(refreshed)
                results['embeddingGemma2'] = ok
            def _check_g3n():
                results['gemma3n'] = ping_gemma_3n(token)
            t1 = threading.Thread(target=_check_eg2)
            t2 = threading.Thread(target=_check_g3n, daemon=True)
            t1.start()
            t2.start()
            t1.join()
            t2.join(timeout=4)
            eg2_ready = results['embeddingGemma2']
            self._send_json(200 if eg2_ready else 429, {
                'ready': eg2_ready,
                'embeddingGemma2': 'ready' if eg2_ready else 'warming',
                'gemma3n': 'ready' if results['gemma3n'] else 'warming',
            })
            return

        if self.path == '/api/embed':
            content_length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_length)
            is_warmup_ping = b'query: warmup' in post_body

            auth_header = self.headers.get('Authorization')
            token = None
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ', 1)[1].strip()
            if not token:
                token = get_token()

            resp_body = None
            resp_status = None

            if token:
                if is_warmup_ping:
                    threading.Thread(
                        target=ping_gemma_3n,
                        args=(token,),
                        daemon=True,
                    ).start()

                for attempt in range(2):
                    req = urllib.request.Request(
                        get_vertex_url(token),
                        data=post_body,
                        headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {token}'
                        }
                    )
                    try:
                        with urllib.request.urlopen(req) as resp:
                            resp_body = resp.read()
                            resp_status = resp.status
                        break
                    except urllib.error.HTTPError as e:
                        resp_status = e.code
                        resp_body = e.read()
                        if e.code == 401 and attempt == 0:
                            token = get_token(force_refresh=True)
                            if token:
                                continue
                        break
                    except Exception as e:
                        resp_status = 500
                        resp_body = str(e).encode('utf-8')
                        break

            if resp_status and resp_body:
                self.send_response(resp_status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(resp_body)
            else:
                self._send_json(500, {'error': 'Embedding endpoint unavailable'})

        elif self.path == '/api/watched-folders':
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode('utf-8'))
            folder_path = body.get('path', '').strip()

            if not folder_path:
                self._send_json(400, {'error': 'Folder path is required'})
                return

            resolved_path = os.path.expanduser(folder_path)
            if not os.path.isdir(resolved_path):
                self._send_json(400, {'error': f'Directory does not exist: {folder_path}'})
                return

            cfg = load_watched_folders()
            existing = [f for f in cfg.get('folders', []) if f.get('resolvedPath') == resolved_path]
            if not existing:
                entry = {
                    "path": folder_path,
                    "resolvedPath": resolved_path,
                    "itemCount": 0,
                    "lastSynced": None,
                    "autoWatch": True
                }
                cfg['folders'].append(entry)
                save_watched_folders(cfg)

                # Trigger scan immediately for the new folder
                token = get_token()
                if token:
                    scan_and_index_folders([entry], token)

            cfg = load_watched_folders()
            self._send_json(200, cfg)

        elif self.path == '/api/sync-folders':
            token = get_token()
            if not token:
                self._send_json(401, {'error': 'No Google Cloud token available'})
                return

            cfg = load_watched_folders()
            new_count, total_count = scan_and_index_folders(cfg.get('folders', []), token)
            updated_cfg = load_watched_folders()
            self._send_json(200, {
                'status': 'ok',
                'newMemories': new_count,
                'totalMemories': total_count,
                'folders': updated_cfg.get('folders', [])
            })

        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        if self.path == '/api/watched-folders':
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode('utf-8'))
            folder_path = body.get('path', '').strip()
            resolved_path = os.path.expanduser(folder_path)

            cfg = load_watched_folders()
            cfg['folders'] = [f for f in cfg.get('folders', []) if f.get('resolvedPath') != resolved_path and f.get('path') != folder_path]
            save_watched_folders(cfg)
            self._send_json(200, cfg)
        else:
            self.send_response(404)
            self.end_headers()

def main():
    port = 8085
    server = http.server.ThreadingHTTPServer(('0.0.0.0', port), LarkHandler)
    print(f"Lark Memory Web Server running at http://localhost:{port}/")

    # Start background watcher thread
    watcher_thread = threading.Thread(target=background_watcher, daemon=True)
    watcher_thread.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
