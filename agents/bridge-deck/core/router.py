#!/usr/bin/env python3
"""
Registry-Driven Agent Router for Bridge Deck.
Dynamically resolves target agents and provider instances from agents/*.agent.json and profiles.json.
Replaces hardcoded mode branching.
"""

import os
import time
import json
import glob
from pathlib import Path
from typing import Dict, Any, Optional, List
from providers.base import AgentProvider
from providers.vertex_anthropic import VertexAnthropicProvider
from providers.vertex_gemini import VertexGeminiProvider
from providers.vertex_custom_endpoint import VertexCustomEndpointProvider
from providers.antigravity_queue import AntigravityQueueProvider
from providers.voyager_harness import VoyagerHarnessProvider
from providers.google_adk import GoogleADKProvider
from providers.ollama_local import OllamaLocalProvider

ROOT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_MODEL: str = "gemini-3.7-flash"

MODEL_ALIASES: Dict[str, str] = {
    "nexus": DEFAULT_MODEL,
    "google adk": DEFAULT_MODEL,
    "adk": DEFAULT_MODEL,
    "gemini 3.7": DEFAULT_MODEL,
    "gemini-3.7": DEFAULT_MODEL,
    "gemini 2.5": "gemini-2.5-flash",
    "gemini-2.5": "gemini-2.5-flash",
    "gemma 4": "gemma-4-26b-a4b-it",
    "gemma-4": "gemma-4-26b-a4b-it",
    "gemma 2": "gemma-2-27b-it",
    "gemma-2": "gemma-2-27b-it",
    "llama-3.3-70b": "llama3.3:70b",
    "llama 3.3": "llama3.3:70b",
    "deepseek-r1": "deepseek-r1:70b",
}


def resolve_model_location(model_str: str) -> str:
    """Derives default region for a model architecture."""
    m = (model_str or "").lower()
    if any(tag in m for tag in ["3.7", "gemini-3", "claude", "maas"]):
        return "global"
    return "us-central1"


class AgentRouter:
    def __init__(self, bridge_dir: Optional[Path] = None):
        from core.tenant import get_tenant_dir
        self.bridge_dir = bridge_dir or get_tenant_dir()
        self.agents_dir = self.bridge_dir / "agents"
        self.providers: Dict[str, AgentProvider] = {}
        self.manifests: Dict[str, Dict[str, Any]] = {}
        self._last_mtime: float = 0
        self._registry_sig = None
        self.schema: Optional[Dict[str, Any]] = None
        self.load_errors: List[Dict[str, Any]] = []
        
        schema_file = self.agents_dir / "_schema.json"
        if schema_file.exists():
            try:
                with open(schema_file, "r", encoding="utf-8") as sf:
                    self.schema = json.load(sf)
            except Exception as e:
                print(f"[!] Error loading agents/_schema.json: {e}")
                
        self.reload_registry()

    def _validate_and_normalize_manifest(self, manifest: Dict[str, Any], filepath: Path) -> Dict[str, Any]:
        """Validates manifest against frozen schema requirements and applies secure-by-default ACL and 3-tier memory."""
        # 1. Check required top-level fields
        if self.schema and "required" in self.schema:
            for req in self.schema["required"]:
                if req not in manifest:
                    raise ValueError(f"Manifest {filepath.name} missing required schema field '{req}'")
        else:
            req_fields = ["id", "name", "role", "provider"]
            for rf in req_fields:
                if rf not in manifest:
                    raise ValueError(f"Manifest {filepath.name} missing required schema field '{rf}'")

        # 2. Schema-based property validation (e.g. enum constraints)
        if self.schema and "properties" in self.schema:
            props = self.schema["properties"]
            for field, field_schema in props.items():
                if field in manifest:
                    # Validate enum
                    if "enum" in field_schema and manifest[field] not in field_schema["enum"]:
                        raise ValueError(
                            f"Manifest {filepath.name} invalid value '{manifest[field]}' for field '{field}'. "
                            f"Must be one of: {field_schema['enum']}"
                        )
                    # Validate type
                    if "type" in field_schema:
                        expected_type = field_schema["type"]
                        if expected_type == "string" and not isinstance(manifest[field], str):
                            raise ValueError(f"Manifest {filepath.name} field '{field}' must be a string")
                        elif expected_type == "array" and not isinstance(manifest[field], list):
                            raise ValueError(f"Manifest {filepath.name} field '{field}' must be an array")
                        elif expected_type == "object" and not isinstance(manifest[field], dict):
                            raise ValueError(f"Manifest {filepath.name} field '{field}' must be an object")

        # 3. Apply secure defaults
        manifest.setdefault("access_read", [])
        manifest.setdefault("access_write", [])
        manifest.setdefault("tools_enabled", [])
        manifest.setdefault("access_notes", "Default secure read-only access.")
        manifest.setdefault("skills", [])
        manifest.setdefault("memory", {"silo": "private", "shared_access": ["*"]})

        # 4. Validate with jsonschema if installed
        try:
            import jsonschema
            if self.schema:
                jsonschema.validate(instance=manifest, schema=self.schema)
        except ImportError:
            pass
        except Exception as se:
            raise ValueError(f"Manifest {filepath.name} schema validation failed: {se}")

        return manifest

    def reload_registry(self, force: bool = False):
        """Loads all agent manifests from agents/*.agent.json with mtime and count caching"""
        manifest_files = list(self.agents_dir.glob("*.agent.json")) if self.agents_dir.exists() else []
        current_max_mtime = max((f.stat().st_mtime for f in manifest_files), default=0)
        profiles_file = self.bridge_dir / "profiles.json"
        p_mtime = profiles_file.stat().st_mtime if profiles_file.exists() else 0
        current_sig = (len(manifest_files), current_max_mtime, p_mtime)

        if not force and self.manifests and getattr(self, "_registry_sig", None) == current_sig:
            return

        self.manifests.clear()
        self.providers.clear()
        self.load_errors.clear()
        
        if not self.agents_dir.exists():
            self.agents_dir.mkdir(parents=True, exist_ok=True)
            
        manifest_files = [f for f in self.agents_dir.glob("*.agent.json") if not f.name.startswith("_")]
        max_mt = 0
        for fpath in manifest_files:
            try:
                max_mt = max(max_mt, fpath.stat().st_mtime)
                with open(fpath, "r", encoding="utf-8") as f:
                    raw_manifest = json.load(f)
                    manifest = self._validate_and_normalize_manifest(raw_manifest, fpath)
                    agent_id = manifest.get("id")
                    if agent_id:
                        self.manifests[agent_id] = manifest
                        provider_inst = self._create_provider(manifest)
                        if provider_inst:
                            self.providers[agent_id] = provider_inst
            except Exception as e:
                err_record = {"file": fpath.name, "error": str(e), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                self.load_errors.append(err_record)
                print(f"[!] Router error loading {fpath.name}: {e}")

        # Check profiles.json for any dynamic profiles not yet in manifests
        if profiles_file.exists():
            pdata = {}
            try:
                with open(profiles_file, "r", encoding="utf-8") as pf:
                    pdata = json.load(pf)
            except Exception as pe:
                err_record = {"file": "profiles.json", "error": str(pe), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                self.load_errors.append(err_record)

            for prof in pdata.get("profiles", []):
                pid = prof.get("id")
                if pid and pid not in self.manifests:
                    try:
                        model_str = MODEL_ALIASES.get((prof.get("model") or "").lower(), prof.get("model") or DEFAULT_MODEL)
                        engine = prof.get("engine", "vertex-ai")
                        endpoint_id = prof.get("endpoint_id")
                        
                        provider_cfg = {
                            "type": engine,
                            "model": model_str,
                            "location": resolve_model_location(model_str)
                        }
                        if endpoint_id or "mg-endpoint" in model_str or engine == "vertex-custom":
                            provider_cfg["type"] = "vertex-custom"
                            if endpoint_id:
                                provider_cfg["endpoint_id"] = endpoint_id
                            elif model_str.startswith("projects/"):
                                provider_cfg["endpoint_id"] = model_str
                        
                        env_project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
                        if env_project and "project_id" not in provider_cfg:
                            provider_cfg["project_id"] = env_project

                        syn_manifest = {
                            "id": pid,
                            "name": prof.get("name", pid),
                            "role": prof.get("role", "Team Member"),
                            "harness": prof.get("harness", "none"),
                            "tools_enabled": prof.get("tools_enabled", []),
                            "system_prompt": prof.get("system_prompt", ""),
                            "access_read": prof.get("access_read", []),
                            "derived_read": prof.get("derived_read", []),
                            "access_write": prof.get("access_write", []),
                            "provider": provider_cfg
                        }
                        norm_mf = self._validate_and_normalize_manifest(syn_manifest, Path(f"{pid}.profile.json"))
                        self.manifests[pid] = norm_mf
                        p_inst = self._create_provider(norm_mf)
                        if p_inst:
                            self.providers[pid] = p_inst
                    except Exception as pe:
                        err_record = {"file": f"{pid}.profile.json", "error": str(pe), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                        self.load_errors.append(err_record)

        self._last_mtime = max_mt
        self._registry_sig = current_sig

    def _create_provider(self, manifest: Dict[str, Any]) -> Optional[AgentProvider]:
        provider_cfg = dict(manifest.get("provider", {}))
        base_r = manifest.get("access_read") or []
        derived_r = manifest.get("derived_read") or []
        provider_cfg["access_read"] = list(dict.fromkeys(base_r + derived_r))
        provider_cfg["access_write"] = manifest.get("access_write", [])
        provider_cfg["tools_enabled"] = manifest.get("tools_enabled", [])
        p_type = provider_cfg.get("type", "").lower()
        model_str = str(provider_cfg.get("model", "")).lower()
        
        # Dedicated custom endpoints (e.g. Model Garden GPU deployments)
        if p_type in ["vertex-custom", "vertex-endpoint", "vertex-custom-endpoint"] or provider_cfg.get("endpoint_id") or "mg-endpoint" in model_str:
            return VertexCustomEndpointProvider(provider_id=manifest["id"], config=provider_cfg)

        # Check if manifest explicitly declares harness: "voyager" for inspection agents (e.g. Lumen)
        if manifest.get("harness") == "voyager" or p_type in ["voyager-harness", "voyager", "antigravity-harness", "antigravity-agent"]:
            return VoyagerHarnessProvider(provider_id=manifest["id"], config=provider_cfg)

        # Standard Vertex AI model routing (Claude Opus -> VertexAnthropicProvider, Gemini -> VertexGeminiProvider)
        if p_type in ["vertex-ai", "vertex", "vertex-anthropic", "vertex-gemini", "google-genai"]:
            model_name = (provider_cfg.get("model") or "").lower()
            if "claude" in model_name or p_type == "vertex-anthropic":
                return VertexAnthropicProvider(provider_id=manifest["id"], config=provider_cfg)
            else:
                return VertexGeminiProvider(provider_id=manifest["id"], config=provider_cfg)

        elif p_type == "google-adk":
            return GoogleADKProvider(provider_id=manifest["id"], config=provider_cfg)
        elif p_type in ["ollama", "ollama-local"]:
            return OllamaLocalProvider(provider_id=manifest["id"], config=provider_cfg)
        elif p_type in ["antigravity-queue", "custom"]:
            return AntigravityQueueProvider(provider_id=manifest["id"], config=provider_cfg)
        elif p_type == "human":
            return None
        else:
            raise ValueError(f"Unknown agent provider type '{p_type}' in manifest for agent '{manifest.get('id')}'")

    def resolve(self, mode: str, recipient: str) -> Optional[Dict[str, Any]]:
        self.reload_registry()
        
        target_id = None
        if mode.endswith("_direct"):
            target_id = mode.replace("_direct", "")
        elif mode in self.manifests:
            target_id = mode
        else:
            rec_lower = (recipient or "").lower()
            for aid, m in self.manifests.items():
                if aid in rec_lower or (m.get("name") and m["name"].lower() in rec_lower):
                    target_id = aid
                    break

        if target_id == "claude" and "lumen" in self.manifests:
            target_id = "lumen"

        return {
            "agent_id": target_id,
            "manifest": self.manifests.get(target_id, {}),
            "provider": self.providers.get(target_id)
        }
