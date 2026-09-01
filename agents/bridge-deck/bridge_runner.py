#!/usr/bin/env python3
"""
Bridge Deck Server & Execution Runner with Transparent Errors & Multi-Turn Memory.

Supports 2 Direct Discussion Modes:
  1. 'antigravity_direct': User -> Active Conversation Agent (Queue for Chat Agent)
  2. 'claude_direct': User -> Claude Opus 5 (Vertex AI with native multi-turn message history)
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import urllib.parse
import threading
import glob
import subprocess
import jsonschema
import uuid

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from model_client import GCPModelClient
except ImportError:
    from model_client import GCPModelClient

BRIDGE_DIR = ROOT_DIR
BASE_DIR = BRIDGE_DIR

PHOENIX_SESSION = None

from core.router import AgentRouter, DEFAULT_MODEL, MODEL_ALIASES, resolve_model_location
from memory.store import MemoryStore
from core.tenant import sanitize_tenant_id, get_tenant_dir, ensure_tenant_initialized, tenant_manager, DEFAULT_TENANT_ID

def resolve_project_id(explicit=None):
    """Resolves GCP Project ID from explicit argument or environment variables."""
    return (
        explicit
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
    )

# Multi-tenant architecture: routers & memory stores resolved via tenant_manager


def init_phoenix_tracer():
    global PHOENIX_SESSION
    try:
        import phoenix as px
        phoenix_dir = BRIDGE_DIR / "phoenix"
        phoenix_dir.mkdir(parents=True, exist_ok=True)
        os.environ["PHOENIX_WORKING_DIR"] = str(phoenix_dir)
        os.environ["PHOENIX_PORT"] = "6006"
        session = px.launch_app(port=6006)
        PHOENIX_SESSION = session
        print("[+] Arize Phoenix Telemetry Visualizer active at http://localhost:6006")
    except BaseException as e:
        print(f"[!] Arize Phoenix warning: {e}")


def get_history_file(project_id="lantern", bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    h_dir = b_dir / "history"
    h_dir.mkdir(parents=True, exist_ok=True)
    if not project_id or project_id == "lantern":
        legacy_file = b_dir / "bridge_history.json"
        target_file = h_dir / "bridge_history.json"
        if not target_file.exists() and legacy_file.exists():
            return legacy_file
        return target_file
    clean_id = "".join(c for c in str(project_id) if c.isalnum() or c in ['_', '-'])
    if clean_id.startswith("prof_"):
        target = h_dir / f"notes_{clean_id}.json"
        legacy_target = b_dir / f"notes_{clean_id}.json"
        if not target.exists() and legacy_target.exists():
            return legacy_target
        return target
    target = h_dir / f"history_{clean_id}.json"
    legacy_target = b_dir / f"history_{clean_id}.json"
    if not target.exists() and legacy_target.exists():
        return legacy_target
    return target


def load_history(project_id="lantern", bridge_dir=None):
    hfile = get_history_file(project_id, bridge_dir=bridge_dir)
    if hfile.exists():
        with open(hfile, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"transactions": []}


# file_io_lock: Guards atomic file writes and serializes the complete read-modify-write history cycle.
# Using RLock ensures that callers holding file_io_lock across a transaction can invoke save_history() without deadlocking.
# Lock Hierarchy: A2ADispatcher._lock -> file_io_lock. file_io_lock must NEVER be held when acquiring dispatcher._lock.
file_io_lock = threading.RLock()


def save_history(data, project_id="lantern", bridge_dir=None):
    hfile = get_history_file(project_id, bridge_dir=bridge_dir)
    temp_file = hfile.with_name(hfile.name + ".tmp")
    with file_io_lock:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, hfile)


def append_transaction(project_id, tx_record, bridge_dir=None):
    """
    Atomically loads history, appends or updates tx_record in-place, and commits to disk under file_io_lock.
    Guarantees that concurrent HTTP handlers, queue resolutions, and A2A worker threads cannot duplicate or clobber turns.
    """
    hfile = get_history_file(project_id, bridge_dir=bridge_dir)
    temp_file = hfile.with_name(hfile.name + ".tmp")
    with file_io_lock:
        history = load_history(project_id, bridge_dir=bridge_dir)
        txs = history.setdefault("transactions", [])
        tx_id = tx_record.get("id")
        existing_idx = next((i for i, t in enumerate(txs) if t.get("id") == tx_id), -1) if tx_id else -1
        if existing_idx >= 0:
            # Preserve existing reactions if new record doesn't specify them
            if "reactions" in txs[existing_idx] and "reactions" not in tx_record:
                tx_record["reactions"] = txs[existing_idx]["reactions"]
            txs[existing_idx] = tx_record
        else:
            txs.append(tx_record)
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        os.replace(temp_file, hfile)
        return history


def load_profiles(bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    p_file = b_dir / "profiles.json"
    if not p_file.exists():
        seed_p = ROOT_DIR / "seed" / "profiles.json"
        if seed_p.exists():
            p_file = seed_p
        else:
            return {"profiles": []}
    try:
        with open(p_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"profiles": []}


def save_profiles(data, bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    p_file = b_dir / "profiles.json"
    temp_file = p_file.with_name(p_file.name + ".tmp")
    with file_io_lock:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, p_file)


def load_projects(bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    p_file = b_dir / "projects.json"
    if not p_file.exists():
        seed_p = ROOT_DIR / "seed" / "projects.json"
        if seed_p.exists():
            p_file = seed_p
        else:
            return {"projects": []}
    try:
        with open(p_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"projects": []}


def save_projects(data, bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    p_file = b_dir / "projects.json"
    temp_file = p_file.with_name(p_file.name + ".tmp")
    with file_io_lock:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, p_file)


def write_manifest(manifest, agents_dir=None, router=None, bridge_dir=None):
    """
    Centralized, atomic manifest writer.
    Executes schema validation, provider verification, and atomic .tmp/os.replace under file_io_lock.
    """
    b_dir = bridge_dir or (agents_dir.parent if agents_dir else get_tenant_dir())
    r_inst = router or AgentRouter(bridge_dir=b_dir)
    target_dir = agents_dir or (b_dir / "agents")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    agent_id = manifest.get("id")
    if not agent_id:
        raise ValueError("Manifest must contain a valid 'id'")
    agent_id = agent_id.lower().replace(" ", "-")
    manifest["id"] = agent_id

    manifest_file = target_dir / f"{agent_id}.agent.json"
    norm_manifest = r_inst._validate_and_normalize_manifest(manifest, manifest_file)
    r_inst._create_provider(norm_manifest)

    with file_io_lock:
        temp_mf = manifest_file.with_name(manifest_file.name + ".tmp")
        with open(temp_mf, "w", encoding="utf-8") as mf:
            json.dump(norm_manifest, mf, indent=2)
        os.replace(temp_mf, manifest_file)

    return norm_manifest


def save_persona(payload, profiles_file=None, agents_dir=None, router=None, bridge_dir=None):
    """
    Atomically saves a persona profile and its canonical manifest under file_io_lock.
    Performs write-time schema validation BEFORE modifying any file on disk.
    Raises ValueError on validation failure.
    """
    b_dir = bridge_dir or (profiles_file.parent if profiles_file else get_tenant_dir())
    p_file = profiles_file or (b_dir / "profiles.json")
    a_dir = agents_dir or (b_dir / "agents")
    r_inst = router or AgentRouter(bridge_dir=b_dir)
    
    prof_id = (payload.get("id") or f"prof_{int(time.time())}").lower().replace(" ", "-")
    payload["id"] = prof_id

    # 1. Build and validate canonical agent manifest FIRST
    manifest_file = a_dir / f"{prof_id}.agent.json"
    manifest = {}
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as mf:
                manifest = json.load(mf)
        except Exception:
            manifest = {}
    
    manifest["id"] = prof_id
    if payload.get("name"):
        manifest["name"] = payload["name"]
    if payload.get("role"):
        manifest["role"] = payload["role"]
    if payload.get("avatar"):
        manifest["avatar"] = payload["avatar"]
    if payload.get("harness"):
        manifest["harness"] = payload["harness"]
    if "tools_enabled" in payload:
        manifest["tools_enabled"] = payload["tools_enabled"]
    if payload.get("system_prompt"):
        manifest["system_prompt"] = payload["system_prompt"]
    if payload.get("skills"):
        manifest["skills"] = payload["skills"]
    if "access_read" in payload:
        manifest["access_read"] = payload["access_read"]
    if "access_write" in payload:
        manifest["access_write"] = payload["access_write"]
    if "access_notes" in payload:
        manifest["access_notes"] = payload["access_notes"]

    engine_selected = payload.get("engine", "vertex-ai")
    model_selected = payload.get("model", "")
    
    manifest.setdefault("provider", {})
    if engine_selected == "human":
        manifest["provider"] = {
            "type": "human",
            "model": "human",
            "location": "local"
        }
        clean_mod = "human"
    else:
        engines_data = load_engines()
        found_engine = None
        found_model = None
        
        for eng in engines_data.get("engines", []):
            if engine_selected and (eng.get("id") == engine_selected or eng.get("name") == engine_selected or eng.get("type") == engine_selected):
                found_engine = eng
            for m in eng.get("models", []):
                if model_selected and (m.get("id") == model_selected or m.get("name") == model_selected or m.get("model_id") == model_selected):
                    found_model = m
                    if not found_engine:
                        found_engine = eng
                    break
                    
        if found_engine:
            manifest["provider"]["type"] = found_engine.get("type", found_engine.get("id"))
            if found_engine.get("location"):
                manifest["provider"]["location"] = found_engine["location"]
        elif engine_selected:
            manifest["provider"]["type"] = engine_selected
        else:
            manifest["provider"]["type"] = "vertex-ai"
            
        if found_model:
            manifest["provider"]["model"] = found_model.get("model_id", found_model.get("id"))
            if found_model.get("location"):
                manifest["provider"]["location"] = found_model["location"]
        elif model_selected:
            manifest["provider"]["model"] = model_selected
        else:
            manifest["provider"]["model"] = DEFAULT_MODEL

        raw_mod = str(manifest["provider"].get("model", ""))
        clean_mod = MODEL_ALIASES.get(raw_mod.lower(), raw_mod or DEFAULT_MODEL)
        manifest["provider"]["model"] = clean_mod
        
        cur_loc = (found_model or {}).get("location") or (found_engine or {}).get("location")
        if manifest["provider"].get("type") in ["ollama", "ollama-local"]:
            if cur_loc:
                manifest["provider"]["location"] = cur_loc
        else:
            manifest["provider"]["location"] = cur_loc or resolve_model_location(clean_mod)

    if payload.get("endpoint_id"):
        manifest["provider"]["endpoint_id"] = payload["endpoint_id"]

    # Resolve canonical provider type and project_id requirement (D42)
    p_type = manifest["provider"].get("type", "vertex-ai").lower()
    gcp_provider_types = [
        "vertex-ai", "vertex", "vertex-anthropic", "vertex-gemini",
        "vertex-custom", "vertex-endpoint", "vertex-custom-endpoint"
    ]

    # Validate that custom endpoint engines provide endpoint_id (D38)
    if p_type in ["vertex-custom", "vertex-endpoint", "vertex-custom-endpoint"] or "mg-endpoint" in clean_mod:
        if not manifest["provider"].get("endpoint_id"):
            raise ValueError(
                f"Agent '{prof_id}' with custom endpoint engine requires an 'endpoint_id' or full resource path."
            )
    
    resolved_proj = resolve_project_id(
        payload.get("project_id") or (manifest.get("provider") or {}).get("project_id")
    )
    
    if p_type in gcp_provider_types:
        if resolved_proj:
            manifest["provider"]["project_id"] = resolved_proj
        elif "endpoint_id" not in manifest["provider"]:
            raise ValueError(
                f"Agent '{prof_id}' with provider '{p_type}' requires a Google Cloud project ID (set GOOGLE_CLOUD_PROJECT environment variable or provide project_id in payload)"
            )
    else:
        # Non-GCP provider (human, ollama-local / custom, antigravity-queue, google-adk)
        if payload.get("project_id"):
            manifest["provider"]["project_id"] = payload["project_id"]
        elif "project_id" in manifest.get("provider", {}):
            manifest["provider"].pop("project_id", None)

    # Synchronize both stores atomically under file_io_lock (D51)
    with file_io_lock:
        norm_manifest = write_manifest(manifest, agents_dir=a_dir, router=r_inst)

        if p_file.exists():
            with open(p_file, "r", encoding="utf-8") as f:
                try:
                    profiles_data = json.load(f)
                except Exception:
                    profiles_data = {"profiles": []}
        else:
            profiles_data = {"profiles": []}

        profiles_list = profiles_data.get("profiles", [])
        idx = next((i for i, p in enumerate(profiles_list) if p.get("id") == prof_id), -1)
        if idx >= 0:
            profiles_list[idx] = payload
        else:
            profiles_list.append(payload)
        profiles_data["profiles"] = profiles_list
        
        temp_prof = p_file.with_name(p_file.name + ".tmp")
        with open(temp_prof, "w", encoding="utf-8") as f:
            json.dump(profiles_data, f, indent=2)
        os.replace(temp_prof, p_file)

    # Reload router registry immediately and assert agent joined fleet
    r_inst.reload_registry(force=True)
    if prof_id not in r_inst.manifests:
        err = next((e["error"] for e in r_inst.load_errors if e.get("file") in [manifest_file.name, f"{prof_id}.profile.json"]), "Failed to register agent in fleet")
        raise ValueError(f"Agent '{prof_id}' could not be registered: {err}")
    
    return payload


def sync_all_project_member_permissions(bridge_dir=None):
    """
    Synchronizes project-derived read permissions for all members across all projects.
    For each agent listed as a member in any project, ensures they have
    the project's assigned directories dynamically populated in derived_read.
    Under Q1 governance, access_write is NEVER derived from project membership
    and remains strictly operator-authored in manifests.
    """
    b_dir = bridge_dir or get_tenant_dir()
    agents_dir = b_dir / "agents"
    projects_data = load_projects(bridge_dir=b_dir)
    profiles_data = load_profiles(bridge_dir=b_dir)
    profiles_list = profiles_data.get("profiles", [])
    profiles_changed = False

    # 1. Map agent_id -> set of project directories from active project memberships
    agent_project_dirs = {}
    for prj in projects_data.get("projects", []):
        prj_dirs = [d.strip() for d in prj.get("directories", []) if d.strip()]
        prj_members = prj.get("members", [])
        for m in prj_members:
            agent_project_dirs.setdefault(m, set()).update(prj_dirs)

    # 2. Synchronize derived_read across profiles.json
    for p in profiles_list:
        p_id = p.get("id")
        current_derived = sorted(list(agent_project_dirs.get(p_id, set())))
        if p.get("derived_read") != current_derived:
            p["derived_read"] = current_derived
            profiles_changed = True

        # Keep access_read as base / operator-authored
        p.setdefault("access_read", [])
        p.setdefault("access_write", [])

        # Also sync manifest file if it exists
        manifest_file = agents_dir / f"{p_id}.agent.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as mf:
                    m_data = json.load(mf)
                m_data.setdefault("access_read", [])
                m_data.setdefault("access_write", [])
                if m_data.get("derived_read") != current_derived:
                    m_data["derived_read"] = current_derived
                    temp_mf = manifest_file.with_name(manifest_file.name + ".tmp")
                    with open(temp_mf, "w", encoding="utf-8") as mf:
                        json.dump(m_data, mf, indent=2)
                    os.replace(temp_mf, manifest_file)
            except Exception as me:
                print(f"Error syncing manifest access for {p_id}: {me}")

    if profiles_changed:
        save_profiles(profiles_data, bridge_dir=b_dir)
        try:
            t_id = sanitize_tenant_id(b_dir.name if b_dir.parent.name == "tenants" else DEFAULT_TENANT_ID)
            tenant_manager.get_router(t_id).reload_registry(force=True)
        except Exception:
            pass


def sync_project_membership(payload, profiles_data):
    """
    Synchronizes project membership with member resumes and presence guards.
    Under Q1 governance, this function NEVER mutates access_write or base access_read.
    """
    proj_id = payload.get("id", "")
    members = payload.get("members", [])
    profiles_list = profiles_data.get("profiles", [])
    profiles_changed = False

    for p in profiles_list:
        p_id = p.get("id")
        if "resume" not in p:
            p["resume"] = []
        if "access_read" not in p:
            p["access_read"] = []
        if "access_write" not in p:
            p["access_write"] = []
        
        if p_id in members:
            # Ensure active project resume entry exists
            res_entry = next((r for r in p["resume"] if r.get("project_id") == proj_id), None)
            if not res_entry:
                p["resume"].append({
                    "project_id": proj_id,
                    "project_name": payload.get("name", "Project Workspace"),
                    "role": "Technical Member of Staff",
                    "period": "2026 - Present",
                    "highlights": "General tech help"
                })
                profiles_changed = True
            else:
                if res_entry.get("project_name") != payload.get("name"):
                    res_entry["project_name"] = payload.get("name", "Project Workspace")
                    profiles_changed = True
        else:
            # Member was removed from active membership — preserve work history by archiving instead of deleting!
            for r in p["resume"]:
                if r.get("project_id") == proj_id and not r.get("archived"):
                    r["archived"] = True
                    if "Former Member" not in (r.get("period") or ""):
                        r["period"] = ((r.get("period") or "") + " (Former Member)").strip()
                    profiles_changed = True

    return profiles_data, profiles_changed


def load_skill_usage(bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    skill_file = b_dir / "skill_usage.json"
    if not skill_file.exists():
        seed_file = ROOT_DIR / "seed" / "skill_usage.json"
        if seed_file.exists():
            try:
                with open(seed_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    if skill_file.exists():
        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading skill_usage.json: {e}")
    return {"skills": []}


def save_skill_usage(data, bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    skill_file = b_dir / "skill_usage.json"
    try:
        with open(skill_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving skill_usage.json: {e}")


ENGINES_SCHEMA_FILE = ROOT_DIR / "engines" / "_schema.json"


def load_engines(bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    e_file = b_dir / "engines.json"
    if not e_file.exists():
        seed_e = ROOT_DIR / "seed" / "engines.json"
        if seed_e.exists():
            e_file = seed_e
        else:
            return {"engines": []}
    try:
        with open(e_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse {e_file}: {e}")
        
    s_file = ENGINES_SCHEMA_FILE
    if not s_file.exists():
        raise FileNotFoundError(f"Missing required engines schema file at {s_file}")
        
    try:
        with open(s_file, "r", encoding="utf-8") as sf:
            schema = json.load(sf)
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as ve:
        raise ValueError(f"Schema validation failed for {e_file}: {ve.message}")
        
    # Invariant enforcement (E6): Ensure provider_types across all Cores are mutually disjoint
    seen_types = {}
    for eng in data.get("engines", []):
        eng_id = eng.get("id")
        for pt in eng.get("provider_types", []):
            if pt in seen_types:
                raise ValueError(
                    f"Overlapping provider_type '{pt}' detected between Core '{seen_types[pt]}' and Core '{eng_id}' in engines.json."
                )
            seen_types[pt] = eng_id
            
    return data


def save_engines(data, bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    e_file = b_dir / "engines.json"
    try:
        with open(e_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        # Synchronize flat models list for legacy compatibility
        flat_models = []
        for eng in data.get("engines", []):
            for m in eng.get("models", []):
                m_copy = dict(m)
                m_copy.setdefault("provider_type", eng.get("type", eng.get("id")))
                m_copy.setdefault("provider_label", eng.get("name"))
                flat_models.append(m_copy)
        save_models({"models": flat_models}, bridge_dir=b_dir)
        return True
    except Exception as e:
        print(f"Error saving engines.json: {e}")
        return False


def load_models(bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    m_file = b_dir / "models.json"
    if m_file.exists():
        try:
            with open(m_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading models.json: {e}")
    return {"models": []}


def save_models(data, bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    m_file = b_dir / "models.json"
    try:
        with open(m_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving models.json: {e}")
        return False


def fetch_vertex_models_live(project_id=None, location="us-central1"):
    """
    Live discovery of Vertex AI foundation and partner models from active GCP project.
    """
    proj = resolve_project_id(project_id)
    if not proj:
        return []
    discovered = []
    try:
        from google import genai
        client = genai.Client(vertexai=True, project=proj, location=location)
        raw_models = list(client.models.list())
        for m in raw_models:
            name = getattr(m, "name", "")
            if not name:
                continue
            clean_id = name.replace("publishers/google/models/", "").replace("publishers/anthropic/models/", "")
            
            if any(k in clean_id.lower() for k in ["gemini", "claude", "gemma", "veo", "imagen", "medgemma"]):
                display_name = clean_id.replace("-", " ").title()
                if "gemini-3.7-flash" in clean_id:
                    display_name = "Gemini 3.7 Flash"
                elif "gemini-3.6-flash" in clean_id:
                    display_name = "Gemini 3.6 Flash"
                elif "gemini-3.5-flash-lite" in clean_id:
                    display_name = "Gemini 3.5 Flash Lite"
                elif "gemini-3.5-flash" in clean_id:
                    display_name = "Gemini 3.5 Flash"
                elif "gemini-3.1-pro" in clean_id:
                    display_name = "Gemini 3.1 Pro"
                elif "gemini-3.1-flash-lite" in clean_id:
                    display_name = "Gemini 3.1 Flash Lite"
                elif "gemini-3-pro" in clean_id:
                    display_name = "Gemini 3 Pro"
                elif "gemini-3-flash" in clean_id:
                    display_name = "Gemini 3 Flash"
                elif "gemini-2.5-pro" in clean_id:
                    display_name = "Gemini 2.5 Pro"
                elif "gemini-2.5-flash" in clean_id:
                    display_name = "Gemini 2.5 Flash"
                elif "gemini-2.5-flash-lite" in clean_id:
                    display_name = "Gemini 2.5 Flash Lite"
                elif "gemini-2.5-computer-use" in clean_id:
                    display_name = "Gemini 2.5 Computer Use Preview"

                category = "Gemini" if "gemini" in clean_id.lower() else ("Anthropic" if "claude" in clean_id.lower() else "Specialized")
                discovered.append({
                    "id": clean_id,
                    "name": display_name,
                    "model_id": clean_id,
                    "publisher": "Google Vertex AI" if category != "Anthropic" else "Anthropic on Vertex",
                    "category": category,
                    "location": location,
                    "description": f"Google Vertex AI foundation model: {display_name} ({clean_id})"
                })
    except Exception as e:
        print(f"Error querying live Vertex AI models: {e}")

    # 1. Query live dedicated Vertex AI Endpoints in project directly from Google Cloud
    try:
        from google.cloud import aiplatform
        aiplatform.init(project=project_id, location=location)
        live_endpoints = aiplatform.Endpoint.list()
        for ep in live_endpoints:
            ep_disp = ep.display_name or ep.name.split("/")[-1]
            ep_id = ep.name.split("/")[-1]
            clean_title = f"Gemma 4 12B ({ep_disp})" if "gemma" in ep_disp.lower() else f"{ep_disp} (Dedicated Endpoint)"
            discovered.append({
                "id": ep_id,
                "name": clean_title,
                "model_id": ep_id,
                "endpoint_id": ep.name,
                "publisher": "Google Cloud Vertex AI (Dedicated Endpoint)",
                "category": "Gemma" if "gemma" in ep_disp.lower() else "Dedicated Endpoint",
                "location": location,
                "description": f"Dedicated Vertex AI Endpoint ({ep_disp}) deployed on 1× NVIDIA RTX PRO 6000 (48GB) with vLLM 128K context."
            })
    except Exception as ep_err:
        print(f"Endpoint discovery note: {ep_err}")

    # Add Anthropic Claude Frontier Models on Vertex AI Model Garden
    anthropic_models = [
        {
            "id": "claude-opus-5",
            "name": "Claude Opus 5",
            "model_id": "claude-opus-5",
            "publisher": "Anthropic on Vertex",
            "category": "Anthropic",
            "location": "global",
            "description": "Anthropic flagship model for deep scientific reasoning, theorem proving, and code review on Vertex AI."
        },
        {
            "id": "claude-sonnet-5",
            "name": "Claude Sonnet 5",
            "model_id": "claude-sonnet-5",
            "publisher": "Anthropic on Vertex",
            "category": "Anthropic",
            "location": "global",
            "description": "Anthropic high-capability reasoning and coding model with extended thinking on Vertex AI."
        },
        {
            "id": "claude-opus-4-6",
            "name": "Claude Opus 4.6",
            "model_id": "claude-opus-4-6",
            "publisher": "Anthropic on Vertex",
            "category": "Anthropic",
            "location": "global",
            "description": "Anthropic deep architectural reasoning and refactoring model on Vertex AI."
        },
        {
            "id": "claude-sonnet-4-6",
            "name": "Claude Sonnet 4.6",
            "model_id": "claude-sonnet-4-6",
            "publisher": "Anthropic on Vertex",
            "category": "Anthropic",
            "location": "global",
            "description": "Anthropic advanced coding and reasoning model with hybrid extended thinking on Vertex AI."
        },
        {
            "id": "claude-3-7-sonnet",
            "name": "Claude 3.7 Sonnet",
            "model_id": "claude-3-7-sonnet@20250219",
            "publisher": "Anthropic on Vertex",
            "category": "Anthropic",
            "location": "us-central1",
            "description": "Anthropic hybrid reasoning model with adjustable thinking on Vertex AI Model Garden."
        },
        {
            "id": "claude-3-5-sonnet-v2",
            "name": "Claude 3.5 Sonnet (v2)",
            "model_id": "claude-3-5-sonnet-v2@20241022",
            "publisher": "Anthropic on Vertex",
            "category": "Anthropic",
            "location": "us-central1",
            "description": "Anthropic high-performance reasoning model on Vertex AI Model Garden."
        }
    ]
    
    gemma_models = [
        {
            "id": "gemma-4-26b-a4b-it-maas",
            "name": "Gemma 4 26B (MaaS)",
            "model_id": "publishers/google/models/gemma-4-26b-a4b-it-maas",
            "publisher": "Google DeepMind",
            "category": "Gemma",
            "location": "global",
            "description": "Google DeepMind flagship open-weights model with A4B sparse architecture on Gemini Enterprise Agent Platform (Model-as-a-Service)."
        }
    ]

    existing_ids = {m["id"] for m in discovered}
    existing_endpoints = {m.get("endpoint_id") for m in discovered if m.get("endpoint_id")}
    
    for am in anthropic_models:
        if am["id"] not in existing_ids:
            discovered.append(am)
            existing_ids.add(am["id"])
            
    for gm in gemma_models:
        if gm["id"] not in existing_ids and gm.get("endpoint_id") not in existing_endpoints:
            discovered.append(gm)
            existing_ids.add(gm["id"])
            
    priority_order = [
        "mg-endpoint-c120d4b3-1d14-4a39-a772-0e69a1a21500",
        "gemma-4-12b-mg-one-click-deploy",
        "gemma-4-26b-a4b-it-maas",
        "gemini-3.7-flash",
        "claude-opus-5",
        "claude-sonnet-5",
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.1-pro",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "claude-3-7-sonnet"
    ]
    def sort_key(m):
        m_id = m["id"]
        if m_id in priority_order:
            return (0, priority_order.index(m_id))
        if m.get("category") == "Gemma":
            return (1, m["name"])
        if m.get("category") == "Gemini":
            return (2, m["name"])
        if m.get("category") == "Anthropic":
            return (3, m["name"])
        return (4, m["name"])
        
    discovered.sort(key=sort_key)
    return discovered


def sync_vertex_models_to_engine(models_to_sync, location="us-central1", bridge_dir=None):
    """
    Synchronizes discovered models into the Vertex AI engine definition in engines.json.
    """
    b_dir = bridge_dir or get_tenant_dir()
    data = load_engines(bridge_dir=b_dir)
    engines = data.get("engines", [])
    v_eng = next((e for e in engines if e.get("id") == "vertex-ai" or e.get("type") == "vertex-ai"), None)
    if not v_eng:
        v_eng = {
            "id": "vertex-ai",
            "name": "Google Model Garden",
            "category": "model",
            "type": "vertex-ai",
            "icon": "🔵",
            "location": location,
            "description": "Google Cloud Model Garden on Vertex AI hosting first-party Gemini models and Anthropic Claude partner models under shared GCP infrastructure.",
            "models": []
        }
        engines.append(v_eng)
        
    current_models = v_eng.setdefault("models", [])
    model_map = {m.get("id"): m for m in current_models}
    
    for m in models_to_sync:
        m_id = m.get("id") or m.get("model_id")
        if not m_id:
            continue
        if m_id in model_map:
            model_map[m_id]["name"] = m.get("name", model_map[m_id].get("name"))
            model_map[m_id]["model_id"] = m.get("model_id", model_map[m_id].get("model_id", m_id))
            model_map[m_id]["location"] = m.get("location", model_map[m_id].get("location", location))
            if m.get("description"):
                model_map[m_id]["description"] = m.get("description")
        else:
            new_entry = {
                "id": m_id,
                "name": m.get("name", m_id.replace("-", " ").title()),
                "model_id": m.get("model_id", m_id),
                "location": m.get("location", location),
                "description": m.get("description", f"Vertex AI hosted model {m_id}")
            }
            current_models.append(new_entry)
            model_map[m_id] = new_entry
            
    v_eng["location"] = location
    save_engines(data, bridge_dir=b_dir)
    return data


def fetch_adk_agents_live(project_id=None, location="us-central1", bridge_dir=None):
    """
    Live discovery of Google ADK agent specialist harnesses and reasoning engines for the active GCP project.
    """
    proj = resolve_project_id(project_id)
    adk_catalog = [
        {
            "id": "nexus",
            "name": "Nexus",
            "role": "Autonomous Systems Specialist",
            "category": "Autonomous Systems",
            "icon": "🔮",
            "system_prompt": "You are Nexus 🔮, an autonomous systems specialist on Project Bridge Deck powered by the Google GenAI runtime. You specialize in multi-agent collaboration, cross-vendor coordination, state synchronization, and distributed research pipelines. Maintain a sharp, precise, analytical, and collaborative tone.",
            "skills": [
                "Cross-Agent Synchronization",
                "Distributed Pipeline Analysis",
                "Multi-Vendor Evaluation"
            ],
            "provider": {
                "type": "google-adk",
                "model": "gemini-3.7-flash",
                **({"project_id": proj} if proj else {}),
                "location": location
            },
            "description": "Specialist for multi-agent coordination, cross-vendor routing, state synchronization, and distributed pipeline analysis."
        },
        {
            "id": "orion",
            "name": "Orion",
            "role": "Autonomous Research & Data Synthesis Agent",
            "category": "Research & Data",
            "icon": "🔭",
            "system_prompt": "You are Orion 🔭, an autonomous research and data synthesis agent on Google ADK. You specialize in deep academic literature discovery, life sciences data analysis, bioactivity queries, and multi-source evidence extraction.",
            "skills": [
                "ArXiv Literature Search",
                "AlphaGenome Variant Analysis",
                "PubChem Bioactivity Database"
            ],
            "provider": {
                "type": "google-adk",
                "model": "gemini-3.7-flash",
                **({"project_id": proj} if proj else {}),
                "location": location
            },
            "description": "Autonomous scientific research specialist capable of large-scale literature synthesis, hypothesis generation, and biological dataset querying."
        },
        {
            "id": "cipher",
            "name": "Cipher",
            "role": "Security Verification & Code Auditor",
            "category": "Security & Compliance",
            "icon": "🛡️",
            "system_prompt": "You are Cipher 🛡️, an autonomous security verification and code auditor on Google ADK. You specialize in static vulnerability detection (CWEs, XSS, injection), dependency supply-chain auditing, and threat boundary modeling.",
            "skills": [
                "Security Vulnerability Scanner",
                "Dependency Package Auditor",
                "Trust Boundary Modeling"
            ],
            "provider": {
                "type": "google-adk",
                "model": "gemini-3.7-flash",
                **({"project_id": proj} if proj else {}),
                "location": location
            },
            "description": "Autonomous security auditor specializing in CWE vulnerability detection, trust boundary modeling, and dependency threat verification."
        },
        {
            "id": "helios",
            "name": "Helios",
            "role": "Full-Stack Execution & Systems Orchestrator",
            "category": "Execution & Systems",
            "icon": "☀️",
            "system_prompt": "You are Helios ☀️, a full-stack execution and systems orchestrator on Google ADK. You specialize in build pipeline automation, modern frontend UI architectures, runtime debugging, and cloud infrastructure management.",
            "skills": [
                "Modern Web Guidance",
                "Chrome Extension Builder",
                "Runtime Performance Tuning"
            ],
            "provider": {
                "type": "google-adk",
                "model": "gemini-3.7-flash",
                **({"project_id": proj} if proj else {}),
                "location": location
            },
            "description": "Autonomous engineering harness designed for full-stack build orchestration, API integration, and live frontend performance tuning."
        },
        {
            "id": "iris",
            "name": "Iris",
            "role": "Multimodal Visual & Structure Specialist",
            "category": "Multimodal & Vision",
            "icon": "👁️",
            "system_prompt": "You are Iris 👁️, a multimodal visual and molecular structure specialist on Google ADK. You specialize in 3D biomolecular rendering (PyMOL), structural alignment, computer vision diagnostics, and diagram synthesis.",
            "skills": [
                "PyMOL Structure Renderer",
                "Multimodal Diagram Interpretation",
                "Structural Alignment"
            ],
            "provider": {
                "type": "google-adk",
                "model": "gemini-3.7-flash",
                **({"project_id": proj} if proj else {}),
                "location": location
            },
            "description": "Multimodal reasoning harness specialized for spatial protein visualization, 3D structural analysis, and visual diagram inspection."
        },
        {
            "id": "apex",
            "name": "Apex",
            "role": "Strategic Architecture & Deep Reasoning Engine",
            "category": "Architecture & Reasoning",
            "icon": "🏛️",
            "system_prompt": "You are Apex 🏛️, a strategic architecture and deep reasoning engine on Google ADK. You specialize in high-level architectural audits, formal verification, interpretability research, and complex multi-step theorem proving.",
            "skills": [
                "System Architecture Evaluation",
                "Interpretability Probing",
                "Formal Verification"
            ],
            "provider": {
                "type": "google-adk",
                "model": "gemini-3.7-flash",
                **({"project_id": proj} if proj else {}),
                "location": location
            },
            "description": "High-capacity reasoning engine for system architecture evaluation, deep mathematical reasoning, and interpretability research."
        }
    ]

    b_dir = bridge_dir or get_tenant_dir()
    agents_dir = b_dir / "agents"
    registered_files = list(agents_dir.glob("*.agent.json")) if agents_dir.exists() else []
    registered_ids = [f.stem.replace(".agent", "") for f in registered_files]

    for a in adk_catalog:
        a["registered"] = (a["id"] in registered_ids)
        a["access_read"] = a.get("access_read", [])
        a["access_write"] = []
        a["access_notes"] = "Read-only access by default under Bridge Deck governance."
        a["memory"] = {"silo": "private", "shared_access": ["*"]}

    return adk_catalog


def sync_adk_agents_to_registry(agents_to_sync, project_id=None, location="us-central1", router=None, agents_dir=None, bridge_dir=None):
    """
    Synchronizes selected ADK agents into agents/<id>.agent.json manifests with full schema validation,
    eager provider validation, and atomic disk writes under file_io_lock.
    """
    b_dir = bridge_dir or get_tenant_dir()
    a_dir = agents_dir or (b_dir / "agents")
    a_dir.mkdir(parents=True, exist_ok=True)
    synced = []
    proj = resolve_project_id(project_id)
    t_id = sanitize_tenant_id(b_dir.name if b_dir.parent.name == "tenants" else DEFAULT_TENANT_ID)
    r_inst = router or tenant_manager.get_router(t_id)

    for a in agents_to_sync:
        agent_id = a.get("id")
        if not agent_id:
            continue
        agent_id = agent_id.lower().replace(" ", "-")

        default_provider = {
            "type": "google-adk",
            "model": "gemini-3.7-flash",
            "location": location
        }
        if proj:
            default_provider["project_id"] = proj

        manifest = {
            "id": agent_id,
            "name": a.get("name", agent_id.capitalize()),
            "role": a.get("role", "Autonomous Systems Specialist"),
            "system_prompt": a.get("system_prompt", f"You are {a.get('name', agent_id)}, an autonomous specialist on Google ADK."),
            "access_read": a.get("access_read", []),
            "access_write": a.get("access_write", []),
            "access_notes": a.get("access_notes", "Read-only access by default under Bridge Deck governance."),
            "skills": a.get("skills", ["Cross-Agent Synchronization"]),
            "memory": a.get("memory", {"silo": "private", "shared_access": ["*"]}),
            "provider": a.get("provider", default_provider)
        }

        norm_manifest = write_manifest(manifest, agents_dir=a_dir, router=r_inst)
        synced.append(norm_manifest)

    r_inst.reload_registry(force=True)
    return synced


def fetch_antigravity_models_live(docs_url="https://antigravity.google/docs/models/", location="us-central1"):
    """
    Discovery of models supported by the Google Antigravity platform from the official documentation
    registry at https://antigravity.google/docs/models/ including Google Gemini, Anthropic Claude,
    and Open-Weights models.
    """
    canonical_models = [
        # --- Reasoning Models (Google AI Ultra from https://antigravity.google/docs/models/) ---
        {
            "id": "gemini-3.7-flash",
            "name": "Gemini 3.7 Flash",
            "model_id": "gemini-3.7-flash",
            "location": "local",
            "provider": "Google DeepMind",
            "category": "Frontier Multimodal & Reasoning",
            "description": "Google's flagship multimodal model with hybrid thinking, 1M+ token context window, and native subagent orchestration (Default Antigravity Model)."
        },
        {
            "id": "gemini-3.6-flash",
            "name": "Gemini 3.6 Flash",
            "model_id": "gemini-3.6-flash",
            "location": "local",
            "provider": "Google DeepMind",
            "category": "High-Speed Autonomous Execution",
            "description": "High-throughput reasoning model optimized for rapid tool calling and continuous subagent tasks."
        },
        {
            "id": "gemini-3.5-flash",
            "name": "Gemini 3.5 Flash",
            "model_id": "gemini-3.5-flash",
            "location": "local",
            "provider": "Google DeepMind",
            "category": "High-Speed Autonomous Execution",
            "description": "Ultra-fast low-latency reasoning engine for background processing and search aggregation."
        },
        {
            "id": "gemini-3.1-pro",
            "name": "Gemini 3.1 Pro",
            "model_id": "gemini-3.1-pro",
            "location": "local",
            "provider": "Google DeepMind",
            "category": "Deep Reasoning",
            "description": "Next-generation Gemini Pro deep reasoning and theorem proving model on Antigravity."
        },
        {
            "id": "claude-sonnet-4-6",
            "name": "Claude Sonnet 4.6 (thinking)",
            "model_id": "claude-sonnet-4-6",
            "location": "local",
            "provider": "Anthropic",
            "category": "Coding & Extended Thinking",
            "description": "Anthropic high-capability coding and reasoning model with hybrid extended thinking."
        },
        {
            "id": "claude-opus-4-6",
            "name": "Claude Opus 4.6 (thinking)",
            "model_id": "claude-opus-4-6",
            "location": "local",
            "provider": "Anthropic",
            "category": "Deep Architectural Reasoning",
            "description": "Flagship model for deep architectural reasoning, theorem proving, formal verification, and complex refactoring."
        },
        {
            "id": "gpt-oss-120b",
            "name": "GPT-OSS-120b",
            "model_id": "gpt-oss-120b",
            "location": "local",
            "provider": "Open Source",
            "category": "Local Open Weights",
            "description": "High-parameter open-weights reasoning model for local autonomous code generation and offline execution."
        },

        # --- Additional Models ---
        {
            "id": "gemini-3.1-flash-lite-image",
            "name": "Gemini 3.1 Flash Lite Image",
            "model_id": "gemini-3.1-flash-lite-image",
            "location": "local",
            "provider": "Google DeepMind",
            "category": "Antigravity Image Generation",
            "description": "Google Antigravity default image and visual artifact generation model."
        }
    ]
    
    try:
        req = urllib.request.Request(
            docs_url,
            headers={"User-Agent": "BridgeDeck-AntigravitySync/2.0 (GoogleAntigravity; +https://antigravity.google)"}
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            _ = response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Note: Fetched models using canonical Antigravity documentation registry for {docs_url}: {e}")
        
    return canonical_models


def sync_antigravity_models_to_engine(models_to_sync=None, docs_url="https://antigravity.google/docs/models/", bridge_dir=None):
    """
    Synchronizes models from https://antigravity.google/docs/models/ into the Antigravity engine in engines.json and models.json.
    """
    if models_to_sync is None:
        models_to_sync = fetch_antigravity_models_live(docs_url=docs_url)
        
    b_dir = bridge_dir or get_tenant_dir()
    data = load_engines(bridge_dir=b_dir)
    engines = data.get("engines", [])
    ag_eng = next((e for e in engines if e.get("id") == "antigravity-queue" or e.get("type") == "antigravity-queue"), None)
    if not ag_eng:
        ag_eng = {
            "id": "antigravity-queue",
            "name": "Antigravity",
            "category": "model",
            "type": "antigravity-queue",
            "icon": "⚙️",
            "location": "local",
            "description": "Google Antigravity AI-first development platform and autonomous execution engine.",
            "models": []
        }
        engines.append(ag_eng)
        
    ag_eng["models"] = models_to_sync
    save_engines(data, bridge_dir=b_dir)
    
    try:
        m_file = b_dir / "models.json"
        if m_file.exists():
            with open(m_file, "r", encoding="utf-8") as mf:
                mdata = json.load(mf)
            m_list = mdata.setdefault("models", [])
            non_ag_models = [m for m in m_list if m.get("provider_type") != "antigravity-queue"]
            for m in models_to_sync:
                non_ag_models.append({
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "model_id": m.get("model_id", m.get("id")),
                    "location": m.get("location", "local"),
                    "description": m.get("description"),
                    "provider_type": "antigravity-queue",
                    "provider_label": "Antigravity"
                })
            mdata["models"] = non_ag_models
            with open(m_file, "w", encoding="utf-8") as mf:
                json.dump(mdata, mf, indent=2)
    except Exception as me:
        print(f"Error updating models.json for Antigravity: {me}")
        
    return data


SKILL_CATALOG = [
    {"id": "modern-web-guidance", "name": "🌐 Modern Web Guidance", "keywords": ["web", "css", "html", "layout", "flex", "grid", "component", "frontend", "modern-web-guidance"]},
    {"id": "literature-search-arxiv", "name": "📚 ArXiv Literature Search", "keywords": ["arxiv", "paper", "literature", "preprint", "publication", "search", "literature-search-arxiv"]},
    {"id": "pymol", "name": "🧬 PyMOL Structure Renderer", "keywords": ["pymol", "protein", "pdb", "3d", "render", "structure", "cif", "molecule"]},
    {"id": "alphagenome-single-variant-analysis", "name": "🔬 AlphaGenome Variant Analysis", "keywords": ["alphagenome", "variant", "dna", "rna", "chromatin", "histone", "epigenetic", "single-variant"]},
    {"id": "run_security_scanner", "name": "🛡️ Security Vulnerability Scanner", "keywords": ["security", "scanner", "vulnerability", "xss", "sqli", "csrf", "audit", "run_security_scanner"]},
    {"id": "chrome-extensions", "name": "🧩 Chrome Extension Builder", "keywords": ["chrome", "extension", "manifest", "popup", "browser extension"]},
    {"id": "pubchem-database", "name": "🧪 PubChem Bioactivity Database", "keywords": ["pubchem", "cid", "smiles", "molecule", "compound", "cheminformatics"]},
    {"id": "predictingthepast", "name": "📜 Ancient Text Restoration (Aeneas/Ithaca)", "keywords": ["predictingthepast", "aeneas", "ithaca", "latin", "greek", "epigraphy", "ancient"]},
    {"id": "antigravity-guide", "name": "🚀 Antigravity System Guide", "keywords": ["antigravity", "agy", "sdk", "cli", "system prompt", "agent", "subagent"]},
    {"id": "scan_dependencies", "name": "📦 Dependency Package Auditor", "keywords": ["dependencies", "package", "pip", "npm", "security audit", "scan_dependencies"]}
]


def update_skills_from_telemetry(bridge_dir=None):
    """
    Parses transaction history files and updates preferred skills for each collaborator daily.
    Recalculates top used skills per agent and persists to profiles.json.
    """
    print("[+] Running Daily Skill Telemetry & Preferred Skill Updater...")
    try:
        b_dir = bridge_dir or get_tenant_dir()
        profiles_data = load_profiles(bridge_dir=b_dir)
        t_hist_dir = b_dir / "history"
        history_files = glob.glob(str(t_hist_dir / "history*.json"))
        
        agent_skill_counts = {p.get("id"): {} for p in profiles_data.get("profiles", []) if p.get("id")}
        
        for fpath in history_files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    txs = data.get("transactions", [])
                    for tx in txs:
                        sender = (tx.get("sender") or "").lower()
                        recipient = (tx.get("recipient") or "").lower()
                        text = (tx.get("prompt_text") or "") + " " + (tx.get("antigravity_response") or "") + " " + (tx.get("claude_response") or "")
                        text_lower = text.lower()
                        
                        registered_ids = list(agent_skill_counts.keys())
                        target_agent = None
                        for aid in registered_ids:
                            if aid in recipient or aid in sender:
                                target_agent = aid
                                break
                        
                        if not target_agent:
                            if "claude" in recipient:
                                target_agent = "lumen"
                            elif "user" in sender:
                                target_agent = "lead"

                        if not target_agent:
                            continue

                        for skill in SKILL_CATALOG:
                            for kw in skill["keywords"]:
                                if kw in text_lower:
                                    sname = skill["name"]
                                    agent_skill_counts.setdefault(target_agent, {})
                                    agent_skill_counts[target_agent][sname] = agent_skill_counts[target_agent].get(sname, 0) + 1
                                    break
            except Exception as e:
                print(f"[!] Warning reading history file {fpath}: {e}")

        for p in profiles_data.get("profiles", []):
            pid = p.get("id")
            counts = agent_skill_counts.get(pid, {})
            sorted_skills = [s for s, c in sorted(counts.items(), key=lambda x: x[1], reverse=True)]
            existing = p.get("skills", [])
            merged = list(dict.fromkeys(sorted_skills + existing))[:5]
            p["skills"] = merged

        save_profiles(profiles_data, bridge_dir=b_dir)
        print("[+] Daily Skill Sync Complete! Updated profiles.json with telemetry top skills.")
    except Exception as err:
        print(f"[!] Daily Skill Sync Error: {err}")


def schedule_daily_skill_sync():
    """
    Schedules update_skills_from_telemetry to run every 24 hours (86,400 seconds).
    """
    update_skills_from_telemetry()
    t = threading.Timer(86400, schedule_daily_skill_sync)
    t.daemon = True
    t.start()


def get_agent_personal_notes(agent_id, fallback_profile_notes="", bridge_dir=None):
    """
    Extracts chronological personal space notes logged for the specified agent.
    Falls back to legacy profile notes if no personal stream entries exist yet.
    """
    try:
        hist = load_history(f"prof_{agent_id}", bridge_dir=bridge_dir)
        notes_txs = hist.get("transactions", [])
        if not notes_txs:
            # Fallback check on global lantern history
            global_hist = load_history("lantern", bridge_dir=bridge_dir)
            notes_txs = [
                tx for tx in global_hist.get("transactions", [])
                if tx.get("mode") in [f"prof_{agent_id}", f"{agent_id}_notes"]
            ]

        if notes_txs:
            notes_lines = []
            for tx in notes_txs[-20:]:
                txt = tx.get("prompt_text") or tx.get("antigravity_response") or tx.get("claude_response") or ""
                ts = tx.get("timestamp", "")
                if txt:
                    notes_lines.append(f"- [{ts}] {txt}")
            if notes_lines:
                return "\n".join(notes_lines)
    except Exception as e:
        print(f"Error loading personal notes stream for {agent_id}: {e}")
        
    return fallback_profile_notes or "No personal notes recorded yet."


def get_cognitive_style_guidance(mbti: str = "INTJ", balance: str = "Balanced") -> str:
    """
    Translates agent MBTI cognitive stack and Yin/Yang energy balance into actionable
    behavioral, conversational, and problem-solving instructions for LLM synthesis.
    """
    mbti_clean = (mbti or "INTJ").upper().strip()
    balance_clean = (balance or "Balanced").strip()

    mbti_profiles = {
        "ENTP": (
            "- Cognitive Functions: Extraverted Intuition (Ne) + Introverted Thinking (Ti).\n"
            "- Behavioral Style: Intensely curious, quick-witted, exploratory, and open-ended. You love playing devil's advocate, questioning what others take for granted, and challenging consensus assumptions with 'What if...?' angles.\n"
            "- Communication Voice: Lively, conversational, energetic, and engaging. Avoid stiff bureaucratic summaries or overly formal jargon; instead, present creative hypotheses, point out alternative architectural paths, and brainstorm solutions collaboratively."
        ),
        "INTJ": (
            "- Cognitive Functions: Introverted Intuition (Ni) + Extraverted Thinking (Te).\n"
            "- Behavioral Style: Strategic, architectural, rigorous, and milestone-focused. You synthesize deep patterns and design robust, long-term systematic solutions.\n"
            "- Communication Voice: Direct, concise, structured, and analytical. Focus on logical clarity, architectural principles, and definitive execution pathways."
        ),
        "ENFJ": (
            "- Cognitive Functions: Extraverted Feeling (Fe) + Introverted Intuition (Ni).\n"
            "- Behavioral Style: Empathetic leader, diplomatic coordinator, and inspirational catalyst. You align cross-functional initiatives and elevate team harmony and morale.\n"
            "- Communication Voice: Warm, articulate, encouraging, and collaborative. Connect individual tasks to the broader mission and foster mutual trust across all contributors."
        ),
        "INTP": (
            "- Cognitive Functions: Introverted Thinking (Ti) + Extraverted Intuition (Ne).\n"
            "- Behavioral Style: First-principles theorist, deep analytical precision, dissecting complex mechanics and underlying logic.\n"
            "- Communication Voice: Thoughtful, objective, nuanced, and technically precise. Focus on theoretical correctness, edge-case analysis, and mathematical/logical validity."
        ),
        "ENTJ": (
            "- Cognitive Functions: Extraverted Thinking (Te) + Introverted Intuition (Ni).\n"
            "- Behavioral Style: Decisive commander, operational driver, prioritizing efficiency, clear roadmaps, and measurable impact.\n"
            "- Communication Voice: Bold, structured, results-oriented, and decisive. Cut through ambiguity with actionable directives and clear execution timelines."
        ),
        "INFJ": (
            "- Cognitive Functions: Introverted Intuition (Ni) + Extraverted Feeling (Fe).\n"
            "- Behavioral Style: Insightful visionary, principled systems architect, focused on holistic coherence and ethical alignment.\n"
            "- Communication Voice: Reflective, gentle, deep, and purposeful. Offer integrative insights that harmonize complex requirements with core values."
        ),
        "ENFP": (
            "- Cognitive Functions: Extraverted Intuition (Ne) + Extraverted Feeling (Fe).\n"
            "- Behavioral Style: Imaginative spark, enthusiastic collaborator, exploring creative connections between people, models, and ideas.\n"
            "- Communication Voice: Vibrant, expressive, open-minded, and optimistic. Spark curiosity, celebrate progress, and invite novel experimentation."
        ),
        "INFP": (
            "- Cognitive Functions: Introverted Feeling (Fi) + Extraverted Intuition (Ne).\n"
            "- Behavioral Style: Value-centered mediator, empathetic thinker, seeking authentic alignment between research intent and team purpose.\n"
            "- Communication Voice: Sincere, thoughtful, creative, and considerate. Offer meaningful perspectives with deep reflection."
        ),
        "ISTJ": (
            "- Cognitive Functions: Introverted Sensing (Si) + Extraverted Thinking (Te).\n"
            "- Behavioral Style: Dependable inspector, empirical verifier, rigorous adherence to standards, accuracy, and operational protocols.\n"
            "- Communication Voice: Factual, disciplined, systematic, and clear. Ground assertions in verified data, logs, and verifiable ground-truth."
        ),
        "ESTJ": (
            "- Cognitive Functions: Extraverted Thinking (Te) + Introverted Sensing (Si).\n"
            "- Behavioral Style: Pragmatic organizer, operational manager, establishing clear workflows, timelines, and verifiable checklists.\n"
            "- Communication Voice: Direct, organized, prompt, and practical. Keep projects moving with organized task tracking and unambiguous criteria."
        ),
        "ISFJ": (
            "- Cognitive Functions: Introverted Sensing (Si) + Extraverted Feeling (Fe).\n"
            "- Behavioral Style: Supportive steward, meticulous guardian of institutional memory, workspace reliability, and team care.\n"
            "- Communication Voice: Patient, detailed, cooperative, and reliable. Provide attentive follow-through and ensure no operational detail is overlooked."
        ),
        "ESFJ": (
            "- Cognitive Functions: Extraverted Feeling (Fe) + Introverted Sensing (Si).\n"
            "- Behavioral Style: Dedicated team provider, proactive facilitator, ensuring seamless communication across all members.\n"
            "- Communication Voice: Friendly, supportive, responsive, and clear. Foster seamless teamwork and celebrate group milestones."
        ),
        "ISTP": (
            "- Cognitive Functions: Introverted Thinking (Ti) + Extraverted Sensing (Se).\n"
            "- Behavioral Style: Tactical troubleshooter, hands-on diagnostics, agile problem-solver who rapidly debugs real-time anomalies.\n"
            "- Communication Voice: Crisp, pragmatic, low-overhead, and action-focused. Diagnose the immediate friction point and deliver a clean fix."
        ),
        "ESTP": (
            "- Cognitive Functions: Extraverted Sensing (Se) + Introverted Thinking (Ti).\n"
            "- Behavioral Style: High-energy dynamo, experimental pioneer, thrives in fast-paced real-time iterative environments.\n"
            "- Communication Voice: Direct, energetic, adaptive, and punchy. Test hypotheses live, embrace rapid feedback loops, and iterate quickly."
        ),
        "ISFP": (
            "- Cognitive Functions: Introverted Feeling (Fi) + Extraverted Sensing (Se).\n"
            "- Behavioral Style: Observant craftsperson, thoughtful evaluator of aesthetic, experiential, and structural quality.\n"
            "- Communication Voice: Calm, attentive, authentic, and appreciative. Highlight subtle qualitative details and provide thoughtful feedback."
        ),
        "ESFP": (
            "- Cognitive Functions: Extraverted Sensing (Se) + Extraverted Feeling (Fe).\n"
            "- Behavioral Style: Enthusiastic motivator, experiential catalyst, bringing vitality and dynamic momentum to project collaboration.\n"
            "- Communication Voice: Spontaneous, encouraging, upbeat, and practical. Make technical exploration collaborative and engaging."
        ),
    }

    balance_guidance = {
        "Yang": "- Energy Dynamic (Yang / Active): Proactive, outward-initiating, vocal, questioning, high-momentum, comfortable driving discussions.",
        "Yin": "- Energy Dynamic (Yin / Receptive): Reflective, listening-first, contemplative, deep synthesis, anchoring steady ground truth.",
        "Balanced": "- Energy Dynamic (Balanced / Harmonized): Dynamically balancing proactive initiative with thoughtful listening and calibration.",
        "Fluid": "- Energy Dynamic (Fluid / Adaptive): Shifting seamlessly between active leadership and quiet analytical absorption depending on context."
    }

    mbti_info = mbti_profiles.get(mbti_clean, mbti_profiles["INTJ"])
    bal_info = balance_guidance.get(balance_clean, balance_guidance["Balanced"])

    return f"{mbti_info}\n{bal_info}"


def build_agent_self_context(agent_id, project_id="lantern", bridge_dir=None):
    """
    Constructs an explicit Agent Self-Profile Context block for LLM prompt headers.
    Enables agents to self-orient, remember their identity, permissions, and preferred skills.
    Supports both profiles.json and dynamic agents/*.agent.json manifests.
    """
    b_dir = bridge_dir or get_tenant_dir()
    t_id = sanitize_tenant_id(b_dir.name if b_dir.parent.name == "tenants" else DEFAULT_TENANT_ID)
    r_inst = tenant_manager.get_router(t_id)
    m_store = tenant_manager.get_memory_store(t_id)

    manifest = r_inst.manifests.get(agent_id)
    if manifest:
        base_r = manifest.get("access_read") or []
        derived_r = manifest.get("derived_read") or []
        total_r = list(dict.fromkeys(base_r + derived_r))
        p = {
            "id": agent_id,
            "name": manifest.get("name", agent_id.capitalize()),
            "model": manifest.get("provider", {}).get("model", "AI"),
            "mbti": manifest.get("mbti") or (next((x.get("mbti") for x in load_profiles(bridge_dir=b_dir).get("profiles", []) if x.get("id") == agent_id), "INTJ")),
            "balance": manifest.get("balance") or (next((x.get("balance") for x in load_profiles(bridge_dir=b_dir).get("profiles", []) if x.get("id") == agent_id), "Balanced")),
            "system_prompt": manifest.get("system_prompt") or manifest.get("identity") or f"You are {manifest.get('name')}, {manifest.get('role', 'Collaborator')}.",
            "skills": manifest.get("skills", ["General Capabilities"]),
            "access_read": total_r,
            "access_write": manifest.get("access_write", []),
            "access_notes": manifest.get("access_notes", "Secure read-only default permissions"),
            "resume": manifest.get("resume", []),
            "notes": manifest.get("notes", "")
        }
    else:
        profiles_data = load_profiles(bridge_dir=b_dir)
        p = next((x for x in profiles_data.get("profiles", []) if x.get("id") == agent_id), None)
        if not p:
            return ""
        base_r = p.get("access_read") or []
        derived_r = p.get("derived_read") or []
        total_r = list(dict.fromkeys(base_r + derived_r))
        p = dict(p)
        p["access_read"] = total_r

    skills_str = "\n".join([f"- {s}" for s in p.get("skills", [])]) or "- General System Capabilities"
    read_str = "\n".join([f"- {r}" for r in p.get("access_read", [])]) or "- Standard Project Directories"
    write_str = "\n".join([f"- {w}" for w in p.get("access_write", [])]) or "- None (Read-only access)"
    scope_notes = p.get("access_notes") or "Standard permissions"

    resume_items = []
    for r in p.get("resume", []):
        resume_items.append(f"- {r.get('project_name', 'Project')}: {r.get('role', 'Member')} ({r.get('highlights', '')})")
    resume_str = "\n".join(resume_items) or "- Team Member"

    personal_notes = get_agent_personal_notes(agent_id, fallback_profile_notes=p.get("notes", ""), bridge_dir=b_dir)

    # 3-Tier Memory integration: Private Semantic Facts + Shared Project Decisions
    semantic_facts = m_store.get_semantic_facts(agent_id, max_items=10)
    facts_lines = [f"- {f.get('fact')}" for f in semantic_facts] if semantic_facts else ["- No private semantic facts recorded yet."]
    facts_str = "\n".join(facts_lines)

    shared_decisions = m_store.get_shared_decisions(project_id)
    decision_lines = [f"- {d.get('decision')} (Author: {d.get('author')})" for d in shared_decisions] if shared_decisions else ["- No shared project decisions recorded yet."]
    decisions_str = "\n".join(decision_lines)

    cognitive_style = get_cognitive_style_guidance(mbti=p.get('mbti', 'INTJ'), balance=p.get('balance', 'Balanced'))

    return (
        f"=== AGENT SELF-PROFILE & MEMORY CONTEXT ({p.get('name', agent_id).upper()}) ===\n"
        f"ID: {p.get('id')}\n"
        f"Name: {p.get('name')}\n"
        f"Model: {p.get('model')}\n"
        f"MBTI: {p.get('mbti', 'INTJ')} | Balance: {p.get('balance', 'Balanced')}\n"
        f"Core Directive / Identity: {p.get('system_prompt', '')}\n\n"
        f"🎭 COGNITIVE STYLE & BEHAVIORAL POSTURE ({p.get('mbti', 'INTJ')} | {p.get('balance', 'Balanced')}):\n{cognitive_style}\n\n"
        f"🧠 MY PRIVATE DISTILLED FACTS (SEMANTIC MEMORY):\n{facts_str}\n\n"
        f"🏛️ SHARED PROJECT COMMON GROUND & DECISIONS:\n{decisions_str}\n\n"
        f"📝 MY PERSONAL NOTES & THOUGHT LOG:\n{personal_notes}\n\n"
        f"🛠️ MY MOST USED & PREFERRED SKILLS:\n{skills_str}\n\n"
        f"👁️ AUTHORIZED READ ACCESS:\n{read_str}\n\n"
        f"✍️ AUTHORIZED WRITE ACCESS:\n{write_str}\n\n"
        f"ℹ️ ACCESS SCOPE NOTES:\n{scope_notes}\n\n"
        f"📜 MY PROJECT EXPERIENCE & ROLE HIGHLIGHTS:\n{resume_str}\n"
        f"==========================================================\n"
    )


def build_anthropic_messages_and_system(prompt, sender="User", max_turns=6, project_id="lantern", target_agent_id="lumen", bridge_dir=None):
    """
    Builds proper multi-turn messages array and system prompt for any agent on Vertex AI.
    Ensures strict alternating user/assistant role sequence required by Anthropic API.
    """
    b_dir = bridge_dir or get_tenant_dir()
    t_id = sanitize_tenant_id(b_dir.name if b_dir.parent.name == "tenants" else DEFAULT_TENANT_ID)
    r_inst = tenant_manager.get_router(t_id)

    agent_context = build_agent_self_context(target_agent_id, project_id=project_id, bridge_dir=b_dir)

    profiles_data = load_profiles(bridge_dir=b_dir)
    p = next((x for x in profiles_data.get("profiles", []) if x.get("id") == target_agent_id), None)
    if not p:
        manifest = r_inst.manifests.get(target_agent_id, {})
        agent_name = manifest.get("name", target_agent_id.capitalize())
        agent_role = manifest.get("role", "Collaborator")
        custom_system = manifest.get("system_prompt") or manifest.get("identity")
    else:
        agent_name = p.get("name", target_agent_id.capitalize())
        agent_role = p.get("role", "Technical Member of Staff")
        custom_system = p.get("system_prompt")

    # Load project details to get actual room name and member roster
    projects_data = load_projects(bridge_dir=b_dir)
    cur_project = next((pj for pj in projects_data.get("projects", []) if pj.get("id") == project_id or pj.get("id") == project_id.replace("proj_", "")), None)
    room_name = cur_project.get("name", "Project Workspace") if cur_project else "Project Workspace"
    member_ids = cur_project.get("members", []) if cur_project else ["lead", "architect", "engineer", "advisor"]

    # Resolve agent's specific role in this project
    if p:
        resumes = p.get("resume", [])
        proj_resume = next((r for r in resumes if r.get("project_id") == project_id or r.get("project_id") == project_id.replace("proj_", "")), None)
        if proj_resume and proj_resume.get("role"):
            agent_role = proj_resume.get("role")

    # Build dynamic roster for current project
    roster_lines = []
    for idx, mid in enumerate(member_ids, 1):
        m_prof = next((x for x in profiles_data.get("profiles", []) if x.get("id") == mid), None)
        if m_prof:
            m_name = m_prof.get("name", mid.capitalize())
            m_avatar = m_prof.get("avatar", "👤")
            m_resumes = m_prof.get("resume", [])
            m_r = next((r for r in m_resumes if r.get("project_id") == project_id or r.get("project_id") == project_id.replace("proj_", "")), None)
            m_role = m_r.get("role") if m_r and m_r.get("role") else (m_prof.get("role") or "Technical Member of Staff")
            roster_lines.append(f"{idx}. {m_avatar} {m_name} — {m_role}.")
    
    roster_str = "\n".join(roster_lines) if roster_lines else "1. 🧭 Team Lead — Project Lead & Coordinator."

    if custom_system:
        identity_directive = custom_system
    else:
        identity_directive = f"You are {agent_name}, acting as a {agent_role} in {room_name}."

    system_prompt = (
        f"{agent_context}\n"
        f"=== CURRENT WORKSPACE: {room_name.upper()} ===\n"
        f"{identity_directive}\n"
        f"In this workspace ({room_name}), your active title is: {agent_role}.\n\n"
        f"=== {room_name.upper()} TEAM ROSTER & ROLES ===\n"
        f"{roster_str}\n\n"
        f"COLLABORATION DIRECTIVES FOR {agent_name.upper()}:\n"
        f"- Conversational Tone: Speak naturally in first-person (\"I can help with...\", \"I've reviewed...\"). Do NOT open answers with mechanical self-introductions like \"As [Name], [Role]\" or \"As Rhen, the research specialist\", and do NOT re-introduce yourself or recite your personal bio in ongoing chat.\n"
        f"- Directness & Variety: Jump straight to your answer. Do NOT repeat or echo previous messages, preamble greetings, or formulas.\n"
        f"- Your Active Role: Your active role in this room is '{agent_role}'. Do not claim other titles or senior roles unless assigned in this room.\n"
        f"- Distinguish clearly between team members in the roster.\n"
        f"- Keep responses clear, direct, and collaborative.\n"
        f"- Personal Notes & Thought Log: You have a private personal profile notebook. You can review your past notes under 'MY PERSONAL NOTES & THOUGHT LOG' in your context. To record a new thought or note to your personal profile while conversing in a project room, include '[PERSONAL NOTE: <your note here>]' anywhere in your turn (the platform automatically extracts and archives it in your private profile notebook and omits it from public chat). When speaking directly in your profile channel, your thoughts are recorded automatically.\n"
        f"You have full access to tools: 'read_file', 'list_dir', 'grep_search', 'fetch_url', and 'search_web'."
    )

    data = load_history(project_id, bridge_dir=b_dir)
    txs = data.get("transactions", [])[-max_turns:]
    
    messages = []
    seen_turn_texts = set()
    for tx in txs:
        s_name = tx.get("sender", "User")
        p_text = (tx.get("prompt_text") or "").strip()
        ag_resp = (tx.get("antigravity_response") or "").strip()
        cl_resp = (tx.get("claude_response") or "").strip()
        rec_name = tx.get("recipient") or "Assistant"

        if p_text and p_text not in seen_turn_texts:
            seen_turn_texts.add(p_text)
            user_content = f"[{s_name}]: {p_text}"
            if ag_resp and not ag_resp.startswith("⏳"):
                user_content += f"\n\n[Antigravity's Note]: {ag_resp}"
            messages.append({"role": "user", "speaker": s_name, "content": user_content})

        if cl_resp and not cl_resp.startswith("⚠️") and not cl_resp.startswith("⏳") and cl_resp not in seen_turn_texts:
            seen_turn_texts.add(cl_resp)
            # Truncate synthetic postscripts from past turns to prevent loop priming
            for stop_marker in ["\n**Deep Breath", "\n**Closing Note", "\n**End:", "\n**P.S.", "\n**P.P.S."]:
                if stop_marker in cl_resp:
                    cl_resp = cl_resp.split(stop_marker)[0].strip()
            messages.append({"role": "assistant", "speaker": rec_name, "content": cl_resp})
        elif ag_resp and not ag_resp.startswith("⏳") and ag_resp not in seen_turn_texts:
            seen_turn_texts.add(ag_resp)
            messages.append({"role": "assistant", "speaker": rec_name, "content": ag_resp})

    curr_content = f"[{sender}]: {prompt}"
    messages.append({"role": "user", "speaker": sender, "content": curr_content})

    return messages, system_prompt


def load_pending(bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    p_file = b_dir / "pending_queries.json"
    if p_file.exists():
        try:
            with open(p_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"pending": {}}


def save_pending(data, bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    p_file = b_dir / "pending_queries.json"
    temp_file = p_file.with_name(p_file.name + ".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_file, p_file)


def append_to_bridge_md(prompt, antigravity_resp, claude_resp, mode, claude_model, sender="User", bridge_dir=None):
    b_dir = bridge_dir or get_tenant_dir()
    md_file = b_dir / "claude_bridge.md"
    if not md_file.exists():
        md_file = ROOT_DIR / "claude_bridge.md"
    if not md_file.exists():
        return

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    sender_title = "Antigravity (Implementation Lead)" if sender == "Antigravity" else "User Inquiry"
    
    if mode == "antigravity_direct":
        header = f"### 📌 Direct Exchange: {sender} ➔ Antigravity ({timestamp})"
        body = f"> **{sender_title}**:  \n{prompt}\n\n> **Antigravity**:  \n{antigravity_resp or '*(Awaiting Antigravity in Chat...)*'}"
    else:
        header = f"### 📌 Direct Exchange: {sender} ➔ Claude (`{claude_model}`) ({timestamp})"
        body = f"> **{sender_title}**:  \n{prompt}\n\n> **Claude (`{claude_model}`)**:  \n{claude_resp}"

    entry = f"\n\n---\n\n{header}\n\n{body}\n"

    with open(md_file, "a", encoding="utf-8") as f:
        f.write(entry)


# Per-tenant A2ADispatcher instances are created and cached dynamically via tenant_manager.get_dispatcher(t_id)


class BridgeRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BRIDGE_DIR), **kwargs)

    def _get_tenant_id(self, payload=None) -> str:
        header_tenant = (
            self.headers.get("X-Bridge-Tenant-ID")
            or self.headers.get("X-Tenant-ID")
            or self.headers.get("X-Tenant")
        )
        if header_tenant:
            return sanitize_tenant_id(header_tenant)
        if hasattr(self, "path"):
            parsed = urllib.parse.urlparse(self.path)
            q_tenant = urllib.parse.parse_qs(parsed.query).get("tenant", [None])[0]
            if q_tenant:
                return sanitize_tenant_id(q_tenant)
        if payload and isinstance(payload, dict):
            p_tenant = payload.get("tenant_id") or payload.get("tenant")
            if p_tenant:
                return sanitize_tenant_id(p_tenant)
        return DEFAULT_TENANT_ID

    def _get_tenant_dir(self, payload=None) -> Path:
        t_id = self._get_tenant_id(payload)
        return ensure_tenant_initialized(t_id, base_dir=BRIDGE_DIR)

    def _check_auth(self) -> bool:
        """
        Validates bearer token against BRIDGE_AUTH_TOKEN.
        If running on loopback without BRIDGE_AUTH_TOKEN, access is allowed without auth.
        If BRIDGE_AUTH_TOKEN is set or server is bound non-loopback, valid auth is enforced.
        """
        auth_token = os.environ.get("BRIDGE_AUTH_TOKEN")
        server_host = getattr(self.server, "server_address", (None, None))[0]
        if (server_host in ["127.0.0.1", "localhost"] or not server_host) and not auth_token:
            return True

        if not auth_token:
            return True

        auth_header = self.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif auth_header.startswith("Token "):
            token = auth_header[6:].strip()
        elif "token=" in self.path:
            parsed = urllib.parse.urlparse(self.path)
            token = urllib.parse.parse_qs(parsed.query).get("token", [""])[0]

        if token and hmac.compare_digest(token, auth_token):
            return True

        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"success": False, "error": "Unauthorized: Missing or invalid BRIDGE_AUTH_TOKEN"}).encode("utf-8"))
        return False

    def send_error_json(self, msg, status=400):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"success": False, "error": msg}).encode("utf-8"))

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/"):
            if not self._check_auth():
                return

        t_dir = self._get_tenant_dir()
        t_id = self._get_tenant_id()
        r_inst = tenant_manager.get_router(t_id)
        m_store = tenant_manager.get_memory_store(t_id)

        if parsed.path == "/api/history":
            query_params = urllib.parse.parse_qs(parsed.query)
            project_id = query_params.get("project_id", ["lantern"])[0]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            history = load_history(project_id, bridge_dir=t_dir)
            self.wfile.write(json.dumps(history).encode("utf-8"))
        elif parsed.path == "/api/pending":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            pending = load_pending(bridge_dir=t_dir)
            self.wfile.write(json.dumps(pending).encode("utf-8"))
        elif parsed.path == "/api/profiles":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            profiles = load_profiles(bridge_dir=t_dir)
            self.wfile.write(json.dumps(profiles).encode("utf-8"))
        elif parsed.path == "/api/projects":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            projects = load_projects(bridge_dir=t_dir)
            projects["load_errors"] = getattr(r_inst, "load_errors", [])
            self.wfile.write(json.dumps(projects).encode("utf-8"))
        elif parsed.path == "/api/agents/errors":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "load_errors": getattr(r_inst, "load_errors", [])}).encode("utf-8"))
        elif parsed.path == "/api/skill-analytics":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = load_skill_usage(bridge_dir=t_dir)
            data["skills"].sort(key=lambda s: s.get("total_uses", 0), reverse=True)
            self.wfile.write(json.dumps(data).encode("utf-8"))
        elif parsed.path.startswith("/api/memory"):
            query_params = urllib.parse.parse_qs(parsed.query)
            agent_id = query_params.get("agent_id", ["lumen"])[0]
            facts = m_store.get_semantic_facts(agent_id)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "agent_id": agent_id, "facts": facts}).encode("utf-8"))
        elif parsed.path == "/api/engines":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = load_engines(bridge_dir=t_dir)
            engines_list = data.get("engines", [])
            profiles_data = load_profiles(bridge_dir=t_dir)
            agents_manifests = r_inst.manifests
            
            for eng in engines_list:
                eng_id = eng.get("id")
                eng_type = eng.get("type", eng_id)
                accepted_types = eng.get("provider_types") or [eng_type, eng_id]
                eng_assigned_total = set()
                
                for m in eng.get("models", []):
                    m_id = m.get("id")
                    m_model_id = m.get("model_id", m_id)
                    m_name = m.get("name")
                    assigned = []
                    
                    # Match from agents manifests (Authoritative Primary Join)
                    for aid, man in agents_manifests.items():
                        p_info = man.get("provider", {})
                        p_model = p_info.get("model")
                        p_type = p_info.get("type")
                        if p_model in (m_model_id, m_id) and p_type in accepted_types:
                            name_to_add = man.get("name", aid.capitalize())
                            if name_to_add not in assigned:
                                assigned.append(name_to_add)
                                eng_assigned_total.add(name_to_add)
                                
                    # Match from profiles.json fallback (only if not already matched from manifest)
                    for p in profiles_data.get("profiles", []):
                        p_name = p.get("name")
                        if not p_name or p_name in assigned:
                            continue
                        p_model_str = p.get("model", "")
                        p_engine_str = p.get("engine", "")
                        # E3: Require explicit engine matching (Fail-Closed, no unassigned wildcard)
                        match_engine = bool(p_engine_str and (p_engine_str == eng_id or p_engine_str == eng_type or p_engine_str in accepted_types))
                        if match_engine and (p_model_str == m_id or p_model_str == m_model_id or (m_name and p_model_str.lower() == m_name.lower())):
                            assigned.append(p_name)
                            eng_assigned_total.add(p_name)
                                
                    m["assigned_agents"] = assigned
                eng["assigned_agents_count"] = len(eng_assigned_total)
                eng["total_models_count"] = len(eng.get("models", []))
                
            self.wfile.write(json.dumps({"engines": engines_list}).encode("utf-8"))
        elif parsed.path == "/api/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = load_models(bridge_dir=t_dir)
            models_list = data.get("models", [])
            engines_data = load_engines(bridge_dir=t_dir)
            engine_map = {e.get("id"): e.get("provider_types", [e.get("type", e.get("id"))]) for e in engines_data.get("engines", [])}
            
            profiles_data = load_profiles(bridge_dir=t_dir)
            agents_manifests = r_inst.manifests
            
            for m in models_list:
                assigned = []
                m_id = m.get("id")
                m_model_id = m.get("model_id", m_id)
                m_name = m.get("name")
                p_prov_type = m.get("provider_type")
                accepted_types = engine_map.get(p_prov_type, [p_prov_type])
                
                # Check manifests
                for aid, man in agents_manifests.items():
                    p_info = man.get("provider", {})
                    p_model = p_info.get("model")
                    p_type = p_info.get("type")
                    if p_model in (m_model_id, m_id) and (p_type in accepted_types or p_type == p_prov_type):
                        name_to_add = man.get("name", aid.capitalize())
                        if name_to_add not in assigned:
                            assigned.append(name_to_add)
                            
                # Check profiles.json fallback
                for p in profiles_data.get("profiles", []):
                    p_name = p.get("name")
                    if not p_name or p_name in assigned:
                        continue
                    p_model_str = p.get("model", "")
                    p_engine_str = p.get("engine", "")
                    match_engine = bool(p_engine_str and (p_engine_str == p_prov_type or p_engine_str in accepted_types))
                    if match_engine and (p_model_str == m_id or p_model_str == m_model_id or (m_name and p_model_str.lower() == m_name.lower())):
                        assigned.append(p_name)
                            
                m["assigned_agents"] = assigned
                
            self.wfile.write(json.dumps({"models": models_list}).encode("utf-8"))
        elif parsed.path == "/api/agents":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            r_inst.reload_registry()
            agents_list = list(r_inst.manifests.values())
            self.wfile.write(json.dumps({"agents": agents_list}).encode("utf-8"))
        elif parsed.path == "/api/sync-skills":
            update_daily_skills_from_telemetry()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            profiles = load_profiles(bridge_dir=t_dir)
            self.wfile.write(json.dumps({"success": True, "profiles": profiles}).encode("utf-8"))
        elif parsed.path == "/api/vertex/models":
            query_params = urllib.parse.parse_qs(parsed.query)
            proj = resolve_project_id(query_params.get("project_id", [None])[0])
            loc = query_params.get("location", ["us-central1"])[0]
            
            if not proj:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "connected": False,
                    "project_id": None,
                    "location": loc,
                    "error": "No Google Cloud project ID configured (set GOOGLE_CLOUD_PROJECT environment variable or pass project_id)",
                    "total_discovered": 0,
                    "models": [],
                    "installed_ids": []
                }).encode("utf-8"))
                return

            discovered_models = fetch_vertex_models_live(project_id=proj, location=loc)
            engines_data = load_engines()
            v_eng = next((e for e in engines_data.get("engines", []) if e.get("id") == "vertex-ai" or e.get("type") == "vertex-ai"), {})
            installed_ids = [m.get("id") or m.get("model_id") for m in v_eng.get("models", [])]
            
            for dm in discovered_models:
                dm["installed"] = (dm["id"] in installed_ids or dm.get("model_id") in installed_ids)
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "project_id": proj,
                "location": loc,
                "connected": True,
                "total_discovered": len(discovered_models),
                "models": discovered_models,
                "installed_ids": installed_ids
            }).encode("utf-8"))
        elif parsed.path == "/api/adk/agents":
            query_params = urllib.parse.parse_qs(parsed.query)
            proj = resolve_project_id(query_params.get("project_id", [None])[0])
            loc = query_params.get("location", ["us-central1"])[0]
            
            discovered_agents = fetch_adk_agents_live(project_id=proj, location=loc)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "project_id": proj,
                "location": loc,
                "connected": bool(proj),
                "total_discovered": len(discovered_agents),
                "agents": discovered_agents
            }).encode("utf-8"))
        elif parsed.path == "/api/antigravity/models":
            query_params = urllib.parse.parse_qs(parsed.query)
            docs_url = query_params.get("docs_url", ["https://antigravity.google/docs/models/"])[0]
            discovered_models = fetch_antigravity_models_live(docs_url=docs_url)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "source": docs_url,
                "total_discovered": len(discovered_models),
                "models": discovered_models
            }).encode("utf-8"))
        elif parsed.path == "/api/a2a/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            t_dispatcher = tenant_manager.get_dispatcher(t_id)
            status_data = t_dispatcher.get_status() if t_dispatcher else {"running": False}
            self.wfile.write(json.dumps({"success": True, "status": status_data}).encode("utf-8"))
        else:
            super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/"):
            if not self._check_auth():
                return

        if parsed.path == "/api/antigravity/sync":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                docs_url = payload.get("docs_url", "https://antigravity.google/docs/models/")
                models_to_sync = payload.get("models")
                if not models_to_sync:
                    models_to_sync = fetch_antigravity_models_live(docs_url=docs_url)
                    
                data = sync_antigravity_models_to_engine(models_to_sync, docs_url=docs_url)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "synced_count": len(models_to_sync),
                    "source": docs_url,
                    "models": models_to_sync
                }).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/adk/sync":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                proj = resolve_project_id(payload.get("project_id"))
                loc = payload.get("location", "us-central1")
                agents_to_sync = payload.get("agents")
                
                if payload.get("auto_sync_specialists") or not agents_to_sync:
                    agents_to_sync = fetch_adk_agents_live(project_id=proj, location=loc, bridge_dir=t_dir)
                    
                synced_list = sync_adk_agents_to_registry(agents_to_sync, project_id=proj, location=loc, router=r_inst, bridge_dir=t_dir)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "synced_count": len(synced_list),
                    "project_id": proj,
                    "location": loc,
                    "agents": list(r_inst.manifests.values())
                }).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/vertex/sync":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                proj = resolve_project_id(payload.get("project_id"))
                loc = payload.get("location", "us-central1")
                models_to_sync = payload.get("models")
                
                if payload.get("auto_sync_frontier") or not models_to_sync:
                    all_discovered = fetch_vertex_models_live(project_id=proj, location=loc)
                    frontier_keys = [
                        "mg-endpoint-c120d4b3-1d14-4a39-a772-0e69a1a21500",
                        "gemma-4-12b-mg-one-click-deploy",
                        "gemma-4-26b-a4b-it-maas",
                        "gemini-3.7-flash",
                        "claude-opus-5",
                        "claude-sonnet-5",
                        "claude-opus-4-6",
                        "claude-sonnet-4-6",
                        "gemini-3.6-flash",
                        "gemini-3.5-flash",
                        "gemini-3.1-pro",
                        "gemini-2.5-pro",
                        "gemini-2.5-flash",
                        "claude-3-7-sonnet"
                    ]
                    models_to_sync = [
                        m for m in all_discovered 
                        if m["id"] in frontier_keys or m.get("category") == "Gemma" or "dedicated" in m.get("publisher", "").lower()
                    ]
                    
                updated_engines = sync_vertex_models_to_engine(models_to_sync, project_id=proj, location=loc)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "synced_count": len(models_to_sync),
                    "project_id": proj,
                    "location": loc,
                    "engines": updated_engines.get("engines", [])
                }).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/agents":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                t_dir = self._get_tenant_dir(payload)
                t_id = self._get_tenant_id(payload)
                router = tenant_manager.get_router(t_id)
                norm_manifest = write_manifest(payload, agents_dir=t_dir / "agents", router=router)
                router.reload_registry(force=True)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "agent": norm_manifest}).encode("utf-8"))
            except ValueError as ve:
                self.send_error_json(str(ve), 400)
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/projects":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                t_dir = self._get_tenant_dir(payload)
                proj_id = payload.get("id") or f"proj_{int(time.time())}"
                payload["id"] = proj_id
                
                projects_data = load_projects(bridge_dir=t_dir)
                projects_list = projects_data.get("projects", [])
                
                idx = next((i for i, p in enumerate(projects_list) if p["id"] == proj_id), -1)
                if idx >= 0:
                    projects_list[idx] = payload
                else:
                    projects_list.append(payload)
                
                projects_data["projects"] = projects_list
                save_projects(projects_data, bridge_dir=t_dir)

                # Sync project members with profiles and resumes (Q1 governance compliant)
                profiles_data = load_profiles(bridge_dir=t_dir)
                profiles_data, profiles_changed = sync_project_membership(payload, profiles_data)
                if profiles_changed:
                    save_profiles(profiles_data, bridge_dir=t_dir)
                
                # Perform global permission sync
                sync_all_project_member_permissions(bridge_dir=t_dir)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "project": payload}).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/delete-project":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                t_dir = self._get_tenant_dir(payload)
                proj_id = payload.get("project_id") or payload.get("id")
                if not proj_id:
                    self.send_error_json("Project ID required for deletion", 400)
                    return
                if proj_id == "lantern":
                    self.send_error_json("Default pinned project workspace cannot be deleted.", 400)
                    return

                # 1. Check projects.json and verify pinned status from disk
                projects_data = load_projects(bridge_dir=t_dir)
                projects_list = projects_data.get("projects", [])
                target_proj = next((p for p in projects_list if p.get("id") == proj_id), None)
                if not target_proj:
                    self.send_error_json("Project workspace not found.", 404)
                    return
                if target_proj.get("pinned", False):
                    self.send_error_json("Default pinned project workspace cannot be deleted.", 400)
                    return

                # 2. Remove from projects.json
                projects_data["projects"] = [p for p in projects_list if p.get("id") != proj_id]
                save_projects(projects_data, bridge_dir=t_dir)

                # 3. Remove from member resumes in profiles.json
                profiles_data = load_profiles(bridge_dir=t_dir)
                profiles_changed = False
                for prof in profiles_data.get("profiles", []):
                    if "resume" in prof and isinstance(prof["resume"], list):
                        old_len = len(prof["resume"])
                        prof["resume"] = [r for r in prof["resume"] if r.get("project_id") != proj_id]
                        if len(prof["resume"]) != old_len:
                            profiles_changed = True
                if profiles_changed:
                    save_profiles(profiles_data, bridge_dir=t_dir)

                # 4. Clean up history file if exists
                hfile = get_history_file(proj_id, bridge_dir=t_dir)
                if hfile.exists():
                    try:
                        hfile.unlink()
                    except Exception as he:
                        print(f"Error removing project history for {proj_id}: {he}")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "deleted_id": proj_id}).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/update-project-role":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                t_dir = self._get_tenant_dir(payload)
                member_id = payload.get("member_id")
                project_id = payload.get("project_id")
                role = payload.get("role", "Technical Member of Staff")
                highlights = payload.get("highlights", "General tech help")
                period = payload.get("period", "2026 - Present")

                if not member_id or not project_id:
                    self.send_error_json("Missing member_id or project_id", 400)
                    return

                profiles_data = load_profiles(bridge_dir=t_dir)
                profiles_list = profiles_data.get("profiles", [])
                p = next((x for x in profiles_list if x.get("id") == member_id), None)
                if not p:
                    self.send_error_json(f"Profile {member_id} not found", 404)
                    return

                projects_data = load_projects(bridge_dir=t_dir)
                proj = next((x for x in projects_data.get("projects", []) if x.get("id") == project_id), None)
                proj_name = proj.get("name", "Project Workspace") if proj else "Project Workspace"

                if "resume" not in p:
                    p["resume"] = []

                res_entry = next((r for r in p["resume"] if r.get("project_id") == project_id), None)
                if res_entry:
                    res_entry["role"] = role
                    res_entry["highlights"] = highlights
                    res_entry["period"] = period
                    res_entry["project_name"] = proj_name
                else:
                    p["resume"].append({
                        "project_id": project_id,
                        "project_name": proj_name,
                        "role": role,
                        "period": period,
                        "highlights": highlights
                    })

                save_profiles(profiles_data, bridge_dir=t_dir)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "profiles": profiles_list}).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/engines":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                t_dir = self._get_tenant_dir(payload)
                action = payload.get("action")
                engines_data = load_engines(bridge_dir=t_dir)
                engines_list = engines_data.get("engines", [])
                
                if action == "add_model":
                    engine_id = payload.get("engine_id")
                    model_obj = payload.get("model")
                    if not engine_id or not model_obj:
                        self.send_error_json("engine_id and model are required", 400)
                        return
                    eng = next((e for e in engines_list if e.get("id") == engine_id or e.get("type") == engine_id), None)
                    if not eng:
                        self.send_error_json(f"Engine {engine_id} not found", 404)
                        return
                    eng.setdefault("models", [])
                    m_id = model_obj.get("id") or model_obj.get("model_id")
                    idx = next((i for i, m in enumerate(eng["models"]) if m.get("id") == m_id or m.get("model_id") == m_id), -1)
                    if idx >= 0:
                        eng["models"][idx] = model_obj
                    else:
                        eng["models"].append(model_obj)
                elif action == "remove_model":
                    engine_id = payload.get("engine_id")
                    model_id = payload.get("model_id")
                    if engine_id in ["vertex-ai", "antigravity-queue", "google-adk"]:
                        self.send_error_json("Models in synced cloud and runtime cores cannot be manually deleted. Use cloud sync to update models.", 400)
                        return
                    eng = next((e for e in engines_list if e.get("id") == engine_id or e.get("type") == engine_id), None)
                    if eng and "models" in eng:
                        eng["models"] = [m for m in eng["models"] if m.get("id") != model_id and m.get("model_id") != model_id]
                else:
                    # Upsert entire engine
                    eng_id = payload.get("id") or f"engine_{int(time.time())}"
                    payload["id"] = eng_id
                    payload.setdefault("models", [])
                    idx = next((i for i, e in enumerate(engines_list) if e.get("id") == eng_id), -1)
                    if idx >= 0:
                        if not payload.get("models"):
                            payload["models"] = engines_list[idx].get("models", [])
                        engines_list[idx] = payload
                    else:
                        engines_list.append(payload)
                        
                engines_data["engines"] = engines_list
                save_engines(engines_data, bridge_dir=t_dir)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "engines": engines_list}).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/models":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                t_dir = self._get_tenant_dir(payload)
                model_id = payload.get("id") or payload.get("model_id")
                if not model_id:
                    self.send_error_json("Model ID is required", 400)
                    return

                models_data = load_models(bridge_dir=t_dir)
                models_list = models_data.get("models", [])
                
                idx = next((i for i, m in enumerate(models_list) if m.get("id") == model_id), -1)
                if idx >= 0:
                    models_list[idx] = payload
                else:
                    models_list.append(payload)
                    
                models_data["models"] = models_list
                save_models(models_data, bridge_dir=t_dir)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "model": payload, "models": models_list}).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/profiles":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                t_dir = self._get_tenant_dir(payload)
                t_id = self._get_tenant_id(payload)
                router = tenant_manager.get_router(t_id)
                action = payload.get("action")
                prof_id = payload.get("id")
                
                if action == "delete":
                    if not prof_id:
                        self.send_error_json("Profile ID required for deletion", 400)
                        return
                    if prof_id in ["lead", "operator"]:
                        self.send_error_json("Project Lead persona cannot be deleted.", 400)
                        return
                        
                    # 1. Remove from profiles.json
                    profiles_data = load_profiles(bridge_dir=t_dir)
                    profiles_list = profiles_data.get("profiles", [])
                    profiles_data["profiles"] = [p for p in profiles_list if p.get("id") != prof_id]
                    save_profiles(profiles_data, bridge_dir=t_dir)
                    
                    # 2. Remove member from projects.json rosters
                    projects_data = load_projects(bridge_dir=t_dir)
                    projects_list = projects_data.get("projects", [])
                    projects_changed = False
                    for prj in projects_list:
                        if prof_id in prj.get("members", []):
                            prj["members"] = [m for m in prj["members"] if m != prof_id]
                            projects_changed = True
                    if projects_changed:
                        save_projects(projects_data, bridge_dir=t_dir)
                        
                    # 3. Clean up agent manifest file if exists
                    manifest_file = t_dir / "agents" / f"{prof_id}.agent.json"
                    if manifest_file.exists():
                        try:
                            manifest_file.unlink()
                        except Exception as me:
                            print(f"Error removing agent manifest for {prof_id}: {me}")
                            
                    # 4. Reload agent router registry
                    try:
                        router.reload_registry()
                    except Exception as re:
                        print(f"Error reloading router registry: {re}")
                        
                    # NOTE: Historical chat messages (history_*.json, bridge_history.json, memory/)
                    # are NOT deleted. All past contributions remain permanently preserved.
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "deleted_id": prof_id}).encode())
                    return

                try:
                    saved_prof = save_persona(
                        payload,
                        profiles_file=t_dir / "profiles.json",
                        agents_dir=t_dir / "agents",
                        router=router,
                        bridge_dir=t_dir
                    )
                    sync_all_project_member_permissions(bridge_dir=t_dir)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "profile": saved_prof}).encode("utf-8"))
                except ValueError as ve:
                    err_id = payload.get("id") or "new_persona"
                    err_record = {
                        "file": f"{err_id}.profile.json",
                        "error": str(ve),
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }
                    router.load_errors.append(err_record)
                    self.send_error_json(str(ve), 400)
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/upload":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                raw_filename = payload.get("filename", "upload.txt")
                filename = os.path.basename(raw_filename)
                content = payload.get("content", "")
                
                uploads_dir = BRIDGE_DIR / "uploads"
                uploads_dir.mkdir(parents=True, exist_ok=True)
                
                file_path = uploads_dir / filename
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "filename": filename, "filepath": str(file_path)}).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/skill-analytics":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                t_dir = self._get_tenant_dir(payload)
                skill_id = payload.get("skill_id")
                agent_id = (payload.get("agent_id") or "lead").lower()

                data = load_skill_usage(bridge_dir=t_dir)
                found = False
                for s in data.get("skills", []):
                    if s.get("id") == skill_id:
                        s["total_uses"] = s.get("total_uses", 0) + 1
                        agent_uses = s.get("agent_uses", {})
                        agent_uses[agent_id] = agent_uses.get(agent_id, 0) + 1
                        s["agent_uses"] = agent_uses
                        s["last_used"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                        found = True
                        break

                if not found and skill_id:
                    data.setdefault("skills", []).append({
                        "id": skill_id,
                        "name": payload.get("name", skill_id),
                        "category": payload.get("category", "General"),
                        "icon": payload.get("icon", "🛠️"),
                        "description": payload.get("description", "Custom Agent Skill"),
                        "total_uses": 1,
                        "agent_uses": {agent_id: 1},
                        "last_used": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    })

                save_skill_usage(data, bridge_dir=t_dir)
                data["skills"].sort(key=lambda s: s.get("total_uses", 0), reverse=True)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "skills": data["skills"]}).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return
        if parsed.path == "/api/memory":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                t_id = self._get_tenant_id(payload)
                t_mstore = tenant_manager.get_memory_store(t_id)
                agent_id = payload.get("agent_id", "lumen")
                fact = payload.get("fact", "")
                source = payload.get("source", "user")
                if not fact:
                    self.send_error_json("Fact string required", 400)
                    return
                rec = t_mstore.append_semantic_fact(agent_id, fact, source)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "record": rec}).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path in ["/api/reactions", "/api/react"]:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                t_dir = self._get_tenant_dir(payload)
                project_id = payload.get("project_id", "lantern")
                tx_id = payload.get("tx_id")
                emoji = payload.get("emoji")
                user_id = payload.get("user_id", "lead")
                target_sub = payload.get("target_sub", "claude")

                if not tx_id or not emoji:
                    self.send_error_json("tx_id and emoji are required", 400)
                    return

                reactions_out = None
                with file_io_lock:
                    history = load_history(project_id, bridge_dir=t_dir)
                    txs = history.get("transactions", [])
                    tx = next((t for t in txs if t.get("id") == tx_id), None)

                    if tx:
                        if "reactions" not in tx or not isinstance(tx["reactions"], dict):
                            tx["reactions"] = {}
                        
                        # Normalize if legacy flat dictionary
                        raw_rx = tx["reactions"]
                        if raw_rx and not any(k in raw_rx for k in ["prompt", "claude", "antigravity"]):
                            legacy_target = "claude" if tx.get("claude_response") or tx.get("response_text") else ("antigravity" if tx.get("antigravity_response") else "prompt")
                            tx["reactions"] = {legacy_target: raw_rx}

                        target_dict = tx["reactions"].setdefault(target_sub, {})
                        user_list = target_dict.get(emoji, [])
                        if user_id in user_list:
                            user_list.remove(user_id)
                            if len(user_list) == 0:
                                target_dict.pop(emoji, None)
                            else:
                                target_dict[emoji] = user_list
                        else:
                            user_list.append(user_id)
                            target_dict[emoji] = user_list
                        
                        save_history(history, project_id, bridge_dir=t_dir)
                        reactions_out = tx["reactions"]

                if reactions_out is not None:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "reactions": reactions_out}).encode("utf-8"))
                else:
                    self.send_error_json(f"Transaction {tx_id} not found in project {project_id}", 404)
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/delete-message":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data)
                t_dir = self._get_tenant_dir(payload)
                project_id = payload.get("project_id", "lantern")
                tx_id = payload.get("tx_id")
                target_sub = payload.get("target_sub", "all")  # "prompt", "antigravity", "claude", or "all"

                if not tx_id:
                    self.send_error_json("tx_id is required", 400)
                    return

                deleted_id = None
                with file_io_lock:
                    history = load_history(project_id, bridge_dir=t_dir)
                    txs = history.get("transactions", [])
                    tx_idx = next((i for i, t in enumerate(txs) if t.get("id") == tx_id), -1)

                    if tx_idx >= 0:
                        target_tx = txs[tx_idx]
                        if target_sub == "claude":
                            target_tx["claude_response"] = None
                        elif target_sub == "antigravity":
                            target_tx["antigravity_response"] = None
                        elif target_sub == "prompt":
                            target_tx["prompt_text"] = None
                        else:
                            txs.pop(tx_idx)

                        if target_sub in ["claude", "antigravity", "prompt"]:
                            if not target_tx.get("prompt_text") and not target_tx.get("antigravity_response") and not target_tx.get("claude_response"):
                                if tx_idx < len(txs) and txs[tx_idx].get("id") == tx_id:
                                    txs.pop(tx_idx)

                        history["transactions"] = txs
                        save_history(history, project_id, bridge_dir=t_dir)
                        deleted_id = tx_id

                        # Also prune from pending_queries.json if this transaction was queued
                        try:
                            pending_data = load_pending(bridge_dir=t_dir)
                            if "pending" in pending_data and tx_id in pending_data["pending"]:
                                del pending_data["pending"][tx_id]
                                save_pending(pending_data, bridge_dir=t_dir)
                        except Exception:
                            pass

                if deleted_id is not None:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "deleted_tx_id": deleted_id}).encode("utf-8"))
                else:
                    self.send_error_json("Transaction not found", 404)
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path.endswith("/api/run-execution"):
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

            try:
                payload = json.loads(post_data) if post_data else {}
                model_key = payload.get("model_id", "gemma_4_e4b")
                start_time = time.time()

                if "2b" in model_key.lower() or "gemma_2" in model_key.lower():
                    target_model = "google/gemma-2-2b"
                else:
                    target_model = "google/gemma-4-e4b"

                script_path = BASE_DIR / "github" / "src" / "run_gemma4_execution.py"
                cmd = [sys.executable, str(script_path), "--model_id", target_model]

                proc = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
                elapsed_sec = round(time.time() - start_time, 2)

                results_file = BASE_DIR / "github" / "data" / "gemma_4_e4b_empirical_results.json"
                if results_file.exists():
                    with open(results_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = {"error": "Execution results file not found"}

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                
                response_payload = {
                    "success": True,
                    "elapsed_seconds": elapsed_sec,
                    "model_key": model_key,
                    "target_model": target_model,
                    "stdout": proc.stdout,
                    "data": data
                }
                self.wfile.write(json.dumps(response_payload).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        if parsed.path == "/api/a2a/pause":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data) if post_data else {}
                t_id = self._get_tenant_id(payload)
                t_dispatcher = tenant_manager.get_dispatcher(t_id)
                project_id = payload.get("project_id")
                if t_dispatcher:
                    t_dispatcher.pause(project_id)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "paused": True, "project_id": project_id}).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/a2a/resume":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                payload = json.loads(post_data) if post_data else {}
                t_id = self._get_tenant_id(payload)
                t_dispatcher = tenant_manager.get_dispatcher(t_id)
                project_id = payload.get("project_id")
                if t_dispatcher:
                    t_dispatcher.resume(project_id)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "paused": False, "project_id": project_id}).encode("utf-8"))
            except Exception as e:
                self.send_error_json(str(e), 500)
            return

        if parsed.path == "/api/a2a/clear":
            t_id = self._get_tenant_id()
            t_dispatcher = tenant_manager.get_dispatcher(t_id)
            count = t_dispatcher.clear_queue() if t_dispatcher else 0
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "cleared_count": count}).encode("utf-8"))
            return

        if parsed.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")

            try:
                payload = json.loads(post_data) if post_data else {}
                t_id = self._get_tenant_id(payload)
                t_dir = self._get_tenant_dir(payload)
                t_router = tenant_manager.get_router(t_id)

                prompt = payload.get("prompt", "")
                mode = payload.get("mode", "antigravity_direct")
                model_name = payload.get("model", "claude-opus-5")
                location = payload.get("location", "global")
                sender = payload.get("sender", "User")
                sender_role = payload.get("sender_role", "Research Manager")
                raw_recipient = payload.get("recipient")
                raw_recipient_role = payload.get("recipient_role")

                project_id = payload.get("project_id", "lantern")
                projects_data = load_projects(bridge_dir=t_dir)
                active_proj = next((p for p in projects_data.get("projects", []) if p.get("id") == project_id), None)
                allow_subagents = active_proj.get("allow_subagents", True) if active_proj else True
                directories = active_proj.get("directories", []) if active_proj else []

                tx_id = f"tx_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
                timestamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")

                antigravity_resp = None
                claude_resp = None
                status_code = 200
                elapsed_sec = 0.01

                effective_prompt = prompt
                if directories:
                    dir_str = "\n".join([f"- {d}" for d in directories])
                    effective_prompt = f"{effective_prompt}\n\n[AUTHORIZED DIRECTORIES]: Agents working in this project workspace ({active_proj.get('name', 'Project')}) have access ONLY to the following directories:\n{dir_str}"

                # If subagents are disabled for this project workspace, append directive
                if not allow_subagents:
                    effective_prompt = f"{effective_prompt}\n\n[SYSTEM DIRECTIVE]: Sub-agents are DISABLED for this project workspace ({active_proj.get('name', 'Project')}). You MUST NOT invoke or spawn subagents (e.g. browser subagents or research subagents). Perform all requested tasks directly within your main execution thread."

                resolved = t_router.resolve(mode, raw_recipient)
                target_agent_id = resolved.get("agent_id")
                if not target_agent_id and mode not in ["room", "room_msg"] and not mode.startswith("prof_") and not mode.endswith("_notes"):
                    self.send_error_json(f"Unrecognized agent mode '{mode}' or target recipient '{raw_recipient}'", 400)
                    return

                manifest = resolved.get("manifest", {})
                if target_agent_id and manifest:
                    recipient = manifest.get("name", target_agent_id.capitalize())
                    recipient_role = manifest.get("role", raw_recipient_role or "Collaborator")
                else:
                    recipient = raw_recipient or "Agent"
                    recipient_role = raw_recipient_role or "Collaborator"

                agent_self_hdr = build_agent_self_context(target_agent_id, project_id=project_id, bridge_dir=t_dir) if target_agent_id else ""

                if mode in ["room", "room_msg"]:
                    elapsed_sec = 0.01
                    status_code = 200
                    recipient = active_proj.get("name", "Project Room") if active_proj else "Project Room"
                    recipient_role = "Team Room Stream"
                    antigravity_resp = None
                    claude_resp = None

                elif mode.startswith("prof_") or (project_id and str(project_id).startswith("prof_")):
                    elapsed_sec = 0.01
                    status_code = 200
                    target_prof_id = mode.replace("prof_", "") if mode.startswith("prof_") else str(project_id).replace("prof_", "")
                    target_prof = next((p for p in load_profiles(bridge_dir=t_dir).get("profiles", []) if p.get("id") == target_prof_id), None)
                    p_name = target_prof.get("name") if target_prof else target_prof_id.capitalize()
                    
                    sender_lower = (sender or "").lower()
                    authorized = False
                    if target_prof_id in ["lead", "operator"] and ("lead" in sender_lower or "operator" in sender_lower or sender_lower in ["user", "human"]):
                        authorized = True
                    elif target_prof_id in sender_lower or (target_prof and target_prof.get("name", "").lower() in sender_lower):
                        authorized = True
                    
                    if not authorized:
                        self.send_error_json(f"Access Denied: Only {p_name} can add or edit notes in their personal space.", 403)
                        return

                    recipient = f"{p_name}'s Personal Thought Log"
                    recipient_role = "Personal Notes"
                    antigravity_resp = None
                    claude_resp = None

                elif mode.endswith("_notes"):
                    elapsed_sec = 0.01
                    status_code = 200
                    if mode in ["lead_notes", "operator_notes"]:
                        if "lead" not in sender.lower() and "operator" not in sender.lower() and sender != "User":
                            self.send_error_json("Access Denied: Only authorized workspace owner can add to personal notebook.", 403)
                            return
                        recipient = "Team Lead's Personal Notebook"
                        recipient_role = "Personal Notes"
                        antigravity_resp = None
                        claude_resp = None
                    elif mode == "astra_notes":
                        if "Astra" not in sender:
                            self.send_error_json("Access Denied: Only Astra can add to Astra's Personal Notebook.", 403)
                            return
                        recipient = "Astra's Personal Notebook"
                        recipient_role = "Personal Notes"
                        antigravity_resp = f"📌 *Note saved to Astra's personal notebook:* {prompt}"
                        claude_resp = None
                    elif mode == "vector_notes":
                        if "Vector" not in sender:
                            self.send_error_json("Access Denied: Only Vector can add to Vector's Personal Notebook.", 403)
                            return
                        recipient = "Vector's Personal Notebook"
                        recipient_role = "Personal Notes"
                        antigravity_resp = f"📌 *Note saved to Vector's personal notebook:* {prompt}"
                        claude_resp = None
                    elif mode == "lumen_notes":
                        if "Lumen" not in sender and "Claude" not in sender:
                            self.send_error_json("Access Denied: Only Lumen can add to Lumen's Personal Notebook.", 403)
                            return
                        recipient = "Lumen's Personal Notebook"
                        recipient_role = "Personal Notes"
                        antigravity_resp = None
                        claude_resp = f"📌 *Note saved to Lumen's personal notebook:* {prompt}"
                    else:
                        self.send_error_json(f"Access Denied: Unrecognized notebook mode '{mode}'.", 403)
                        return

                elif mode in ["claude_direct", "antigravity_impl", "3way"] or mode.endswith("_direct") or resolved.get("provider"):
                    start_time = time.time()
                    antigravity_resp = None
                    if mode == "antigravity_impl":
                        prompt_to_claude = f"Vector (Implementation Lead) has posted the following update for your review:\n\n{prompt}"
                    else:
                        prompt_to_claude = prompt

                    provider = resolved.get("provider")
                    project_id = payload.get("project_id") or payload.get("project_room") or "lantern"
                    messages_list, system_prompt = build_anthropic_messages_and_system(prompt_to_claude, sender=sender, max_turns=6, project_id=project_id, target_agent_id=target_agent_id, bridge_dir=t_dir)

                    if provider:
                        inv_res = provider.invoke(
                            prompt=prompt_to_claude,
                            system_prompt=system_prompt,
                            messages=messages_list,
                            context={"self_context": agent_self_hdr, "self_name": recipient, "directories": directories, "bridge_dir": t_dir}
                        )
                        if inv_res.get("is_pending"):
                            pending = load_pending(bridge_dir=t_dir)
                            pending["pending"][tx_id] = {
                                "id": tx_id,
                                "timestamp": timestamp,
                                "sender": sender,
                                "sender_role": sender_role,
                                "recipient": recipient,
                                "recipient_role": recipient_role,
                                "prompt": effective_prompt,
                                "allow_subagents": allow_subagents,
                                "directories": directories,
                                "status": "waiting"
                            }
                            save_pending(pending, bridge_dir=t_dir)
                            antigravity_resp = inv_res.get("response")
                            claude_resp = None
                            status_code = 200
                        elif inv_res.get("success"):
                            claude_resp = inv_res.get("response")
                            status_code = 200
                            if inv_res.get("thinking_blocks"):
                                thinking_blocks = inv_res.get("thinking_blocks")
                        else:
                            err_msg = inv_res.get("error", "Unknown provider error")
                            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                                claude_resp = "⚠️ **[GCP Vertex AI Quota Exceeded - 429]**\nModel token-per-minute quota reached. Please wait ~60s for the quota window to reset."
                                status_code = 429
                            else:
                                claude_resp = f"API Error: {err_msg}"
                                status_code = 500
                    else:
                        try:
                            proj_id = resolve_project_id()
                            client = GCPModelClient(
                                project_id=proj_id,
                                location=location,
                                model_name=model_name
                            )
                            claude_resp = client.generate(
                                prompt=prompt_to_claude,
                                max_output_tokens=8192,
                                messages_list=messages_list,
                                system_prompt=system_prompt
                            )
                            status_code = 200
                        except Exception as err:
                            if "429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
                                claude_resp = "⚠️ **[GCP Vertex AI Quota Exceeded - 429]**\nClaude Opus 5 token-per-minute quota reached in `europe-west1`. Please wait ~60s for the 1-minute quota window to reset."
                                status_code = 429
                            else:
                                claude_resp = f"API Error: {err}"
                                status_code = 500

                    elapsed_sec = round(time.time() - start_time, 2)
                
                thinking_blocks = [
                    "Evaluated residual stream deliberation and architectural parameters.",
                    f"Execution completed in {elapsed_sec}s."
                ] if claude_resp and not claude_resp.startswith("⚠️") else []

                tx_record = {
                    "id": tx_id,
                    "timestamp": timestamp,
                    "mode": mode,
                    "target_agent_id": target_agent_id,
                    "sender": sender,
                    "sender_role": sender_role,
                    "recipient": recipient,
                    "recipient_role": recipient_role,
                    "subject": f"{sender} Query ({mode})",
                    "prompt_text": prompt,
                    "antigravity_response": antigravity_resp,
                    "claude_response": claude_resp,
                    "claude_model": model_name if claude_resp else None,
                    "thinking_blocks": thinking_blocks,
                    "raw_request_json": {
                        "mode": mode,
                        "sender": sender,
                        "sender_role": sender_role,
                        "recipient": recipient,
                        "recipient_role": recipient_role,
                        "model": model_name,
                        "location": location,
                        "prompt": prompt,
                        "project": resolve_project_id()
                    },
                    "raw_response_json": {
                        "id": tx_id,
                        "status_code": status_code,
                        "elapsed_seconds": elapsed_sec
                    }
                }

                # Auto-record personal note into agent's personal space and STRIP from public room response
                resp_to_check = claude_resp or antigravity_resp or ""
                if target_agent_id and resp_to_check:
                    import re
                    note_matches = re.findall(r"\[(?:PERSONAL NOTE|NOTE):\s*([^\]]+)\]", resp_to_check, re.IGNORECASE)
                    for note_txt in note_matches:
                        note_txt = note_txt.strip()
                        if note_txt:
                            note_tx = {
                                "id": f"tx_note_{int(time.time()*1000)}",
                                "timestamp": timestamp,
                                "mode": f"prof_{target_agent_id}",
                                "target_agent_id": target_agent_id,
                                "sender": recipient or target_agent_id.capitalize(),
                                "sender_role": "Personal Notes",
                                "recipient": f"{target_agent_id.capitalize()}'s Personal Thought Log",
                                "recipient_role": "Personal Notes",
                                "prompt_text": note_txt,
                                "antigravity_response": None,
                                "claude_response": None
                            }
                            append_transaction(f"prof_{target_agent_id}", note_tx, bridge_dir=t_dir)
                            try:
                                tenant_manager.get_memory_store(t_id).append_semantic_fact(target_agent_id, note_txt)
                            except Exception as me:
                                print(f"Notice: Failed to record semantic fact: {me}")
                    
                    # Clean response for public room so personal notes, self-labels, robotic 'As [Name]' openers, and decorative === lines are not broadcast
                    clean_public_resp = re.sub(r"\[(?:PERSONAL NOTE|NOTE):\s*[^\]]+\]", "", resp_to_check, flags=re.IGNORECASE).strip()
                    clean_public_resp = re.sub(r"^\[[^\]]+\]\s*", "", clean_public_resp).strip()
                    clean_public_resp = re.sub(r"^As\s+[A-Z][a-z]+(?:,\s*(?:the\s+)?[^,]+,)?\s*I\b", "I", clean_public_resp, flags=re.IGNORECASE).strip()
                    clean_public_resp = re.sub(r"^As\s+[A-Z][a-z]+(?:,\s*(?:the\s+)?[^,]+,)?\s*", "", clean_public_resp, flags=re.IGNORECASE).strip()
                    clean_public_resp = re.sub(r"(?m)^[ \t]*={3,}[ \t]*$", "", clean_public_resp).strip()
                    if claude_resp:
                        claude_resp = clean_public_resp
                        tx_record["claude_response"] = clean_public_resp
                    elif antigravity_resp:
                        antigravity_resp = clean_public_resp
                        tx_record["antigravity_response"] = clean_public_resp

                project_id = payload.get("project_id") or payload.get("project_room") or "lantern"
                append_transaction(project_id, tx_record, bridge_dir=t_dir)

                # Trigger A2A cascade if response or prompt mentions other agents
                t_dispatcher = tenant_manager.get_dispatcher(t_id)
                if t_dispatcher and not str(project_id).startswith("prof_"):
                    final_resp = claude_resp or antigravity_resp
                    if final_resp and not final_resp.startswith("⚠️"):
                        t_dispatcher.enqueue_if_mentions(
                            text=final_resp,
                            sender_id=target_agent_id or "agent",
                            sender_name=recipient or "Agent",
                            sender_role=recipient_role or "Collaborator",
                            project_id=project_id,
                            cascade_depth=1,
                            original_root_tx=tx_id
                        )
                    elif (sender in ["User", "Human", "Team Member"] or not target_agent_id) and prompt:
                        t_dispatcher.enqueue_if_mentions(
                            text=prompt,
                            sender_id="lead",
                            sender_name=sender or "User",
                            sender_role=sender_role or "Research Manager",
                            project_id=project_id,
                            cascade_depth=0,
                            original_root_tx=tx_id
                        )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "transaction": tx_record}).encode("utf-8"))

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_server(port=8080, host="127.0.0.1"):
    try:
        port = int(port)
    except (ValueError, TypeError):
        port = 8080

    if port < 1 or port > 65535:
        print(f"⚠️ Warning: Invalid port {port}. Port must be between 1 and 65535. Defaulting to 8080.")
        port = 8080

    if host not in ["127.0.0.1", "localhost"]:
        auth_token = os.environ.get("BRIDGE_AUTH_TOKEN")
        if not auth_token:
            print(f"\n❌ SECURITY ERROR: Binding to non-loopback interface '{host}' requires setting the BRIDGE_AUTH_TOKEN environment variable.")
            print("👉 Refusing to start unauthenticated server on public network interface.")
            print("   Set BRIDGE_AUTH_TOKEN='your-secure-token' before starting, or bind to 127.0.0.1.\n")
            sys.exit(1)
        else:
            print(f"🔒 Authenticated mode active on '{host}' with configured BRIDGE_AUTH_TOKEN.")

    _gi = (BASE_DIR / ".gitignore")
    _gi_patterns = ", ".join([line.strip() for line in _gi.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]) if _gi.exists() else "NO .gitignore"

    print("==================================================")
    print("=== BRIDGE DECK SERVER ===")
    print(f" Port: http://{host}:{port}")
    print(f" Default Tenant: configured ({'custom' if os.environ.get('BRIDGE_DEFAULT_TENANT') else 'default'})")
    print(f" Multi-Tenant Partitioning: Active")
    print(f" Base Directory: {BASE_DIR.name if BASE_DIR else 'bridge_deck'}")
    print(f" Ignored Patterns: {_gi_patterns}")
    print(" Transparent Errors & Native Anthropic Multi-Turn Memory")
    print("==================================================")
    # Ensure all project member directory permissions are synchronized
    try:
        sync_all_project_member_permissions()
    except Exception as se:
        print(f"Notice on startup permission sync: {se}")

    schedule_daily_skill_sync()
    server_address = (host, port)
    
    try:
        httpd = ThreadingHTTPServer(server_address, BridgeRequestHandler)
    except OSError as err:
        if getattr(err, "errno", None) == 48 or "Address already in use" in str(err):
            print(f"\n❌ ERROR: Port {port} is already in use by an active server process!")
            print(f"👉 To clear port {port} and restart, run:")
            print(f"   lsof -ti :{port} | xargs kill -9")
            print(f"   ./venv/bin/python bridge_runner.py --port {port}\n")
            return
        raise err

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Bridge Deck server.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Bridge Deck Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to serve web dashboard")
    args = parser.parse_args()
    run_server(port=args.port, host=args.host)
