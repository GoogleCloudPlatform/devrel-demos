"""Configuration settings for Personal Tech-Briefing Digest Agent."""

import os
from pathlib import Path

# Base data directory (defaults to /data if present for GCS Volume Mount, else ./data)
_default_data_dir = "/data" if os.path.exists("/data") else "./data"
DATA_DIR = Path(os.getenv("DATA_DIR", _default_data_dir)).resolve()

# State and digest output directories
STATE_DIR = DATA_DIR / "state"
DIGESTS_DIR = DATA_DIR / "digests"
SEEN_URLS_FILE = STATE_DIR / "seen_urls.json"

# Concurrency & retention settings
MAX_CONCURRENCY: int = int(os.getenv("MAX_CONCURRENCY", "4"))
RETENTION_DAYS: int = int(os.getenv("RETENTION_DAYS", "30"))
SCHEDULE_INTERVAL_HOURS: int = int(os.getenv("SCHEDULE_INTERVAL_HOURS", "6"))

# Model configuration
DEFAULT_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Inbound Webhook Authentication Secret (optional: if set, requests must pass X-Agent-Secret header)
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")

# Default developer interests profile focusing on Agents, AI, and Cloud Applications
DEFAULT_INTERESTS: list[str] = [
    "AI Agents & Multi-Agent Frameworks",
    "Agent Development Kit (ADK) & Agentic Workflows",
    "Cloud AI Infrastructure & Model Serving (Cloud Run, Vertex AI, GKE)",
    "Agent Reflection, Reasoning Loops & Tool Calling",
    "Retrieval-Augmented Generation (RAG) & Vector Storage on Cloud",
    "LLM Evaluation, Guardrails & Production Observability",
    "Sandboxed Code Execution & Cloud Agent Security",
    "Stateful Serverless Architectures for AI Daemons",
]

# Default RSS/Atom feeds strictly focused on requested architectural publications and practitioner communities
DEFAULT_FEEDS: list[str] = [
    # Architectural & Engineering Publications
    "https://simonwillison.net/atom/entries/",
    "https://www.latent.space/feed",
    "https://www.langchain.com/blog/rss.xml",
    "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_engineering.xml",
    "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
    "https://eugeneyan.com/rss/",
    "https://huyenchip.com/feed",
    "https://lilianweng.github.io/lil-log/feed.xml",

    # Practitioner Reddit Signals
    "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=week",
    "https://www.reddit.com/r/googlecloud/top/.rss?t=week",
]

def ensure_directories() -> None:
    """Ensure required data, state, and digest directories exist."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        DIGESTS_DIR.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        # Allow running in read-only / restricted environments without crashing on import
        pass

# Attempt directory initialization on import
ensure_directories()

