#!/usr/bin/env python3
"""
Canonical Multi-Agent Conversation History Synthesizer.
Formats multi-turn messages for prompt context across all providers (Claude, Gemini, ADK),
ensuring exact speaker attribution, self-marking (you), and zero fabricated speech.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json


import re

_known_prefixes_cache: Dict[tuple, List[str]] = {}


def get_known_prefixes(bridge_dir: Optional[Path] = None) -> List[str]:
    """Dynamically resolves canonical persona names from profiles and manifests with mtime caching."""
    if bridge_dir is None:
        from core.tenant import get_tenant_dir
        b_dir = get_tenant_dir()
    else:
        b_dir = bridge_dir
    agents_dir = b_dir / "agents"
    p_file = b_dir / "profiles.json"
    
    mtime = 0
    if agents_dir.exists():
        try:
            mtime = max((f.stat().st_mtime for f in agents_dir.glob("*.agent.json")), default=0)
        except Exception:
            mtime = 0
    if p_file.exists():
        try:
            mtime = max(mtime, p_file.stat().st_mtime)
        except Exception:
            pass
            
    cache_key = (str(b_dir), mtime)
    if cache_key in _known_prefixes_cache:
        return _known_prefixes_cache[cache_key]
        
    prefixes: List[str] = []
    
    # 1. Discover from profiles.json
    if p_file.exists():
        try:
            with open(p_file, "r", encoding="utf-8") as pf:
                p_data = json.load(pf)
                for p in p_data.get("profiles", []):
                    name = p.get("name")
                    if name and name not in prefixes:
                        prefixes.append(name)
        except Exception:
            pass
            
    # 2. Discover from agents/*.agent.json
    if agents_dir.exists():
        for f in agents_dir.glob("*.agent.json"):
            try:
                with open(f, "r", encoding="utf-8") as af:
                    m = json.load(af)
                    name = m.get("name")
                    if name and name not in prefixes:
                        prefixes.append(name)
            except Exception:
                pass
                
    _known_prefixes_cache[cache_key] = prefixes
    return prefixes


def clean_speaker_name(speaker: Optional[str], bridge_dir: Optional[Path] = None) -> str:
    """Normalizes speaker strings to canonical agent names without raw model slugs."""
    if not speaker:
        return "Assistant"
    s = str(speaker).strip()
    
    # Clean model ID or engine annotations in parentheses, e.g. " (Claude Opus 5)"
    s_base = re.sub(r"\s*\([^)]*\)", "", s).strip()
    
    known_prefixes = get_known_prefixes(bridge_dir)
    for prefix in sorted(known_prefixes, key=len, reverse=True):
        if s.lower().startswith(prefix.lower()) or (s_base and s_base.lower().startswith(prefix.lower())):
            return prefix
    return s_base or s


def format_history_block(
    messages: Optional[List[Dict[str, Any]]],
    self_name: Optional[str] = None,
    bridge_dir: Optional[Path] = None
) -> str:
    """
    Synthesizes messages into a unified, clean '=== RECENT CONVERSATION HISTORY ===' block.
    Supports exact speaker attribution, self-identification, and skips placeholder turns.
    """
    if not messages or len(messages) <= 1:
        return ""

    hist_parts = []
    canonical_self = clean_speaker_name(self_name, bridge_dir=bridge_dir) if self_name else None

    # Exclude the very last message which is the current prompt turn
    for turn in messages[:-1]:
        role = turn.get("role", "user")
        raw_speaker = turn.get("speaker") or ("User" if role == "user" else "Assistant")
        speaker = clean_speaker_name(raw_speaker, bridge_dir=bridge_dir)
        c_text = turn.get("content", "")
        
        if isinstance(c_text, list):
            c_text = " ".join([str(b.get("text", "")) for b in c_text if isinstance(b, dict)])

        if not c_text or not isinstance(c_text, str):
            continue

        c_text = c_text.strip()
        # Skip empty or placeholder turns
        if turn.get("is_placeholder") or not c_text:
            continue

        # Self-marking for reading model: [Lumen (you)]: or [Astra (you)]:
        if canonical_self and canonical_self.lower() == speaker.lower():
            label = f"{speaker} (you)"
        else:
            label = speaker

        # Avoid redundant prefixing if text already has speaker header
        if c_text.startswith(f"[{speaker}]:"):
            c_text_body = c_text[len(f"[{speaker}]:"):].strip()
            hist_parts.append(f"[{label}]: {c_text_body}")
        elif c_text.startswith(f"[{label}]:"):
            hist_parts.append(c_text)
        else:
            hist_parts.append(f"[{label}]: {c_text}")

    if not hist_parts:
        return ""

    return "\n\n=== RECENT CONVERSATION HISTORY ===\n" + "\n\n".join(hist_parts) + "\n===================================="
