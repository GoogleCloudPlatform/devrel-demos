"""FastAPI Web Server and Background Runner for Personal Tech-Briefing Digest Agent.

Provides:
- GET / & GET /digest/latest: HTML reader view for the latest generated briefing.
- GET /api/digests: List all generated digests on disk/GCS volume.
- GET /api/digest/{filename}: Retrieve specific digest markdown content.
- POST /api/generate: Trigger on-demand digest generation guarded by an execution mutex lock.
- GET /healthz: Health check endpoint for Cloud Run monitoring.
- Background scheduler: Periodically generates daily digests in the background.
- Graceful shutdown handler for SIGTERM signals.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import html
import logging
import os
from pathlib import Path
import re
import signal
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from digest_agent.agent import execute_digest_workflow, summarize_single_alert
from digest_agent.config import (
    DIGESTS_DIR,
    POLL_INTERVAL_MINUTES,
    RETENTION_DAYS,
    SCHEDULE_INTERVAL_HOURS,
    SEEN_URLS_FILE,
    STATE_DIR,
    WEBHOOK_SECRET,
    ensure_directories,
)
from digest_agent.schemas import DailyDigest, UserInterests
from digest_agent.utils import atomic_save_text, record_seen_urls

logger = logging.getLogger("digest_agent.server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Execution mutex: Cloud Run Instances runs as a singleton, but concurrent API + background tasks
# must be serialized to avoid file write contention.
workflow_mutex = asyncio.Lock()

# Background scheduler task handle
_background_task: asyncio.Task | None = None
_is_shutting_down = False


class GenerateRequest(BaseModel):
    """Payload for on-demand digest generation."""
    topics: list[str] | None = Field(default=None, description="Custom list of technical topics")
    max_articles: int = Field(default=5, ge=1, le=20, description="Max articles to curate")
    feeds: list[str] | None = Field(default=None, description="Custom RSS/Atom feed URLs")
    force_refresh: bool = Field(default=False, description="Ignore seen URLs cache")


class WebhookPayload(BaseModel):
    """Payload for real-time inbound notification alerts (tweets, GitHub releases, custom links)."""
    url: str | None = Field(default=None, description="Direct URL to article, tweet, or GitHub release")
    text: str | None = Field(default=None, description="Direct text or tweet message body")
    title: str | None = Field(default=None, description="Optional title or headline")
    author: str | None = Field(default=None, description="Optional author or handle (e.g. @GoogleDeepMind)")
    source: str = Field(default="webhook", description="Notification origin (e.g. tweet, github, alert, manual)")


def _format_inline(text: str) -> str:
    """Format inline markdown elements: code, bold, italics, links."""
    escaped = html.escape(text)
    # Inline code
    escaped = re.sub(r"`([^`]+)`", r'<code class="inline-code">\1</code>', escaped)
    # Bold
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    # Italics
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    # Markdown links
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^\)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener noreferrer" class="ext-link">\1 <span class="arrow-icon">↗</span></a>',
        escaped,
    )
    # Anchor jump links
    escaped = re.sub(
        r"\[([^\]]+)\]\((#[^\)]+)\)",
        r'<a href="\2" class="toc-jump-link">\1</a>',
        escaped,
    )
    return escaped


def _markdown_to_html(markdown_text: str) -> str:
    """Convert Markdown text into styled semantic HTML blocks."""
    lines = markdown_text.splitlines()
    blocks = []
    in_list = False
    in_code_block = False
    code_lang = ""
    code_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                code_text = html.escape("\n".join(code_lines))
                blocks.append(f'<pre class="code-block language-{code_lang}"><code>{code_text}</code></pre>')
                in_code_block = False
                code_lines = []
            else:
                if in_list:
                    blocks.append("</ul>")
                    in_list = False
                in_code_block = True
                code_lang = stripped[3:].strip()
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                blocks.append('<ul class="styled-list">')
                in_list = True
            item_text = _format_inline(stripped[2:])
            blocks.append(f'<li><span class="bullet-icon">▸</span><div class="list-text">{item_text}</div></li>')
            continue
        elif re.match(r"^\d+\.\s+", stripped):
            if not in_list:
                blocks.append('<ol class="styled-ordered-list">')
                in_list = True
            item_text = _format_inline(re.sub(r"^\d+\.\s+", "", stripped))
            blocks.append(f'<li><div class="list-text">{item_text}</div></li>')
            continue
        else:
            if in_list:
                blocks.append("</ul>")
                in_list = False

        if not stripped:
            continue

        if stripped.startswith("# "):
            blocks.append(f'<h1 class="main-heading">{_format_inline(stripped[2:])}</h1>')
        elif stripped.startswith("## "):
            blocks.append(f'<h2 class="section-heading">{_format_inline(stripped[3:])}</h2>')
        elif stripped.startswith("### "):
            blocks.append(f'<h3 class="subsection-heading">{_format_inline(stripped[4:])}</h3>')
        elif stripped.startswith("#### "):
            blocks.append(f'<h4 class="card-subheading">{_format_inline(stripped[5:])}</h4>')
        elif stripped.startswith("**Source:**"):
            # Rich article metadata bar
            meta_parts = [p.strip() for p in stripped.split("•")]
            meta_html_items = []
            for part in meta_parts:
                if "Hacker News" in part:
                    meta_html_items.append('<span class="badge-source badge-hn"><span class="badge-icon">🟠</span> Hacker News</span>')
                elif "Source:" in part:
                    src_name = re.sub(r"\*\*Source:\*\*", "", part).strip()
                    meta_html_items.append(f'<span class="badge-source"><span class="badge-icon">📰</span> {html.escape(src_name)}</span>')
                elif "Read time:" in part:
                    rtime = re.sub(r"\*\*Read time:\*\*", "", part).strip()
                    meta_html_items.append(f'<span class="pill">⏱️ {html.escape(rtime)}</span>')
                elif "Engagement:" in part:
                    eng = re.sub(r"\*\*Engagement:\*\*", "", part).strip()
                    meta_html_items.append(f'<span class="pill">{html.escape(eng)}</span>')
                elif "Published:" in part:
                    pub = re.sub(r"\*\*Published:\*\*", "", part).strip()
                    meta_html_items.append(f'<span class="pill">📅 {html.escape(pub)}</span>')
                elif "Verified Source" in part:
                    meta_html_items.append('<span class="pill pill-active"><span class="dot"></span> Verified Source</span>')
                else:
                    meta_html_items.append(f'<span class="pill">{_format_inline(part)}</span>')
            blocks.append(f'<div class="status-pills" style="margin: 0.75rem 0 1rem 0;">{"".join(meta_html_items)}</div>')
        elif stripped.startswith("**Links:**"):
            # Action button bar
            link_matches = re.findall(r"\[([^\]]+)\]\((https?://[^\)]+)\)", stripped)
            if link_matches:
                btn_items = []
                orig_url = link_matches[0][1]
                for label, href in link_matches:
                    if "Original Article" in label or "Read Article" in label:
                        btn_items.append(f'<a href="{html.escape(href)}" target="_blank" rel="noopener noreferrer" class="btn btn-primary">📖 Read Original Article ↗</a>')
                    elif "Discussion" in label or "Hacker News" in label:
                        btn_items.append(f'<a href="{html.escape(href)}" target="_blank" rel="noopener noreferrer" class="btn btn-action-secondary">💬 {html.escape(label)} ↗</a>')
                    else:
                        btn_items.append(f'<a href="{html.escape(href)}" target="_blank" rel="noopener noreferrer" class="btn btn-action-secondary">🔗 {html.escape(label)} ↗</a>')
                btn_items.append(f'<button onclick="copyLink(\'{orig_url}\', this)" class="btn btn-copy">📋 Copy Link</button>')
                blocks.append(f'<div class="action-bar">{"".join(btn_items)}</div>')
            else:
                blocks.append(f'<p class="prose-p">{_format_inline(stripped)}</p>')
        elif stripped.startswith("> "):
            raw_quote = stripped[2:].strip()
            if raw_quote.startswith("**Project/Tool Overview:**"):
                label = "🛠️ Project / Tool Overview"
                raw_quote = raw_quote[len("**Project/Tool Overview:**"):].strip()
                quote_text = _format_inline(raw_quote)
                blocks.append(f'<blockquote class="tldr-quote"><div class="tldr-label">{label}</div><div class="tldr-text">{quote_text}</div></blockquote>')
            elif raw_quote.startswith("**TL;DR:**"):
                label = "⚡ TL;DR"
                raw_quote = raw_quote[len("**TL;DR:**"):].strip()
                quote_text = _format_inline(raw_quote)
                blocks.append(f'<blockquote class="tldr-quote"><div class="tldr-label">{label}</div><div class="tldr-text">{quote_text}</div></blockquote>')
            elif raw_quote.startswith("**Developer Insight:**") or raw_quote.startswith("**Community Insight:**"):
                label = "💬 Developer Insight"
                raw_quote = re.sub(r"^\*\*(?:Developer|Community)\s+Insight:\*\*", "", raw_quote).strip()
                quote_text = _format_inline(raw_quote)
                blocks.append(f'<blockquote class="tldr-quote insight-quote"><div class="tldr-label">{label}</div><div class="tldr-text">{quote_text}</div></blockquote>')
            else:
                quote_text = _format_inline(raw_quote)
                blocks.append(f'<blockquote class="standard-quote"><div class="standard-quote-text">{quote_text}</div></blockquote>')
        elif stripped == "---":
            blocks.append('<hr class="section-divider"/>')
        elif stripped.startswith("<a id=") or stripped.startswith("<a name="):
            blocks.append(stripped)
        else:
            blocks.append(f'<p class="prose-p">{_format_inline(line)}</p>')

    if in_code_block:
        code_text = html.escape("\n".join(code_lines))
        blocks.append(f'<pre class="code-block language-{code_lang}"><code>{code_text}</code></pre>')
    if in_list:
        blocks.append("</ul>")

    return "\n".join(blocks)


def _render_html_page(title: str, markdown_text: str) -> str:
    """Render a modern developer-first Single Page Application and reading interface."""
    body_html = _markdown_to_html(markdown_text)

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - Personal Tech Briefing</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #090d16;
            --bg-surface: #111827;
            --bg-surface-elevated: #1e293b;
            --bg-card: #0f172a;
            --bg-card-hover: #17223b;
            --bg-glass: rgba(17, 24, 39, 0.75);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(56, 189, 248, 0.4);
            --text-main: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.25);
            --accent-hover: #7dd3fc;
            --accent-gradient: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
            --btn-bg: #1e293b;
            --btn-text: #f8fafc;
            --btn-border: rgba(255, 255, 255, 0.12);
            --badge-bg: rgba(56, 189, 248, 0.12);
            --badge-text: #38bdf8;
            --tldr-bg: rgba(56, 189, 248, 0.06);
            --tldr-border: #38bdf8;
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            --font-mono: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            --shadow-card: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
            --shadow-hover: 0 12px 30px -4px rgba(0, 0, 0, 0.6), 0 0 15px var(--accent-glow);
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
        }}

        [data-theme="light"] {{
            --bg-base: #f8fafc;
            --bg-surface: #ffffff;
            --bg-surface-elevated: #f1f5f9;
            --bg-card: #ffffff;
            --bg-card-hover: #f8fafc;
            --bg-glass: rgba(255, 255, 255, 0.85);
            --border-color: #e2e8f0;
            --border-hover: #0284c7;
            --text-main: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --accent: #0284c7;
            --accent-glow: rgba(2, 132, 199, 0.2);
            --accent-hover: #0369a1;
            --accent-gradient: linear-gradient(135deg, #0284c7 0%, #6366f1 100%);
            --btn-bg: #f1f5f9;
            --btn-text: #0f172a;
            --btn-border: #cbd5e1;
            --badge-bg: rgba(2, 132, 199, 0.1);
            --badge-text: #0284c7;
            --tldr-bg: rgba(2, 132, 199, 0.05);
            --tldr-border: #0284c7;
            --shadow-card: 0 4px 16px -2px rgba(15, 23, 42, 0.08);
            --shadow-hover: 0 10px 24px -3px rgba(15, 23, 42, 0.12);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            font-family: var(--font-sans);
            background-color: var(--bg-base);
            color: var(--text-main);
            line-height: 1.65;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            transition: background-color 0.25s ease, color 0.25s ease;
        }}

        /* Header Bar */
        .app-header {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: var(--bg-glass);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-color);
            padding: 0.85rem 1.5rem;
            transition: border-color 0.2s ease;
        }}

        .header-container {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }}

        .brand-section {{
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }}

        .brand-icon {{
            width: 36px;
            height: 36px;
            border-radius: var(--radius-sm);
            background: var(--accent-gradient);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            color: #ffffff;
            box-shadow: 0 0 12px var(--accent-glow);
        }}

        .brand-meta {{
            display: flex;
            flex-direction: column;
        }}

        .brand-title {{
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .brand-subtitle {{
            font-size: 0.75rem;
            color: var(--text-muted);
            font-family: var(--font-mono);
        }}

        .status-pills {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            flex-wrap: wrap;
        }}

        .pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.25rem 0.65rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-family: var(--font-mono);
            font-weight: 500;
            border: 1px solid var(--border-color);
            background: var(--bg-surface);
        }}

        .pill-active {{
            color: #10b981;
            border-color: rgba(16, 185, 129, 0.3);
            background: rgba(16, 185, 129, 0.08);
        }}

        .pill-active .dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: #10b981;
            box-shadow: 0 0 8px #10b981;
            animation: pulse-dot 2s infinite;
        }}

        @keyframes pulse-dot {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.5; transform: scale(0.85); }}
        }}

        .pill-cost {{
            color: #38bdf8;
            border-color: rgba(56, 189, 248, 0.3);
            background: rgba(56, 189, 248, 0.08);
        }}

        .header-actions {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.45rem;
            padding: 0.5rem 0.95rem;
            border-radius: var(--radius-sm);
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            font-family: var(--font-sans);
            text-decoration: none;
            border: 1px solid var(--btn-border);
            background: var(--btn-bg);
            color: var(--btn-text);
        }}

        .btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }}

        .btn-primary {{
            background: var(--accent-gradient);
            color: #ffffff;
            border: none;
            box-shadow: 0 2px 10px var(--accent-glow);
        }}

        .btn-primary:hover {{
            opacity: 0.95;
            box-shadow: 0 4px 16px var(--accent-glow);
        }}

        .btn-primary:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}

        .btn-icon-only {{
            width: 36px;
            height: 36px;
            padding: 0;
            border-radius: var(--radius-sm);
        }}

        /* Toast / Notification Banner */
        #notification-toast {{
            position: fixed;
            bottom: 1.5rem;
            right: 1.5rem;
            z-index: 1000;
            padding: 0.75rem 1.25rem;
            border-radius: var(--radius-md);
            background: var(--bg-surface-elevated);
            color: var(--text-main);
            border: 1px solid var(--accent);
            box-shadow: var(--shadow-hover);
            font-size: 0.88rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            pointer-events: none;
        }}

        #notification-toast.show {{
            transform: translateY(0);
            opacity: 1;
            pointer-events: auto;
        }}

        /* Main App Layout */
        .app-layout {{
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
            padding: 1.5rem;
            display: grid;
            grid-template-columns: 310px 1fr;
            gap: 2rem;
            align-items: start;
            flex: 1;
        }}

        @media (max-width: 960px) {{
            .app-layout {{
                grid-template-columns: 1fr;
            }}
        }}

        /* Sidebar Styles */
        .app-sidebar {{
            position: sticky;
            top: 5rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }}

        .sidebar-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 1.25rem;
            box-shadow: var(--shadow-card);
        }}

        .sidebar-title {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-muted);
            font-weight: 700;
            font-family: var(--font-mono);
            margin-bottom: 0.85rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .search-wrapper {{
            position: relative;
            margin-bottom: 0.5rem;
        }}

        .search-input {{
            width: 100%;
            padding: 0.65rem 0.85rem 0.65rem 2.2rem;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border-color);
            background: var(--bg-surface);
            color: var(--text-main);
            font-size: 0.85rem;
            font-family: var(--font-sans);
            outline: none;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }}

        .search-input:focus {{
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }}

        .search-icon {{
            position: absolute;
            left: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 0.85rem;
            pointer-events: none;
        }}

        .search-shortcut {{
            position: absolute;
            right: 0.6rem;
            top: 50%;
            transform: translateY(-50%);
            background: var(--bg-surface-elevated);
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 0.7rem;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            border: 1px solid var(--border-color);
            pointer-events: none;
        }}

        .topic-filter-chips {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-top: 0.75rem;
        }}

        .topic-chip {{
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
            border: 1px solid var(--border-color);
            background: var(--bg-surface);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .topic-chip:hover, .topic-chip.active {{
            background: var(--badge-bg);
            color: var(--badge-text);
            border-color: var(--accent);
        }}

        .toc-list {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            max-height: 380px;
            overflow-y: auto;
            padding-right: 0.25rem;
        }}

        .toc-item a {{
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
            padding: 0.4rem 0.6rem;
            border-radius: var(--radius-sm);
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.82rem;
            line-height: 1.4;
            transition: all 0.15s ease;
        }}

        .toc-item a:hover, .toc-item a.active {{
            background: var(--bg-surface-elevated);
            color: var(--accent);
        }}

        .toc-item .toc-num {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--accent);
            font-weight: 600;
            flex-shrink: 0;
        }}

        .archive-select {{
            width: 100%;
            padding: 0.6rem 0.85rem;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border-color);
            background: var(--bg-surface);
            color: var(--text-main);
            font-size: 0.82rem;
            font-family: var(--font-mono);
            outline: none;
            cursor: pointer;
        }}

        /* Main Content Container */
        .main-reader-content {{
            display: flex;
            flex-direction: column;
            gap: 1.75rem;
        }}

        /* Prose & Card Styles */
        .content-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 1.75rem;
            box-shadow: var(--shadow-card);
            transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
            position: relative;
        }}

        .content-card:hover {{
            border-color: var(--border-hover);
        }}

        .content-card.article-highlight {{
            box-shadow: 0 0 0 2px var(--accent), var(--shadow-hover);
        }}

        .main-heading {{
            font-size: 1.85rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 0.75rem;
            color: var(--text-main);
        }}

        .section-heading {{
            font-size: 1.35rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-top: 0.5rem;
            margin-bottom: 0.75rem;
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}

        .subsection-heading {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            color: var(--accent);
        }}

        .card-subheading {{
            font-size: 0.95rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            margin-top: 1.25rem;
            margin-bottom: 0.6rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}

        .prose-p {{
            font-size: 0.96rem;
            color: var(--text-secondary);
            margin-bottom: 0.85rem;
            line-height: 1.7;
        }}

        /* Grounded Action Bar */
        .action-bar {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin: 1rem 0;
            flex-wrap: wrap;
        }}

        .btn-action-primary {{
            background: var(--accent-gradient);
            color: #ffffff;
            font-weight: 600;
            font-size: 0.82rem;
            padding: 0.45rem 0.85rem;
            border-radius: var(--radius-sm);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border: none;
            transition: all 0.2s ease;
        }}

        .btn-action-primary:hover {{
            box-shadow: 0 4px 12px var(--accent-glow);
            transform: translateY(-1px);
        }}

        .btn-action-secondary {{
            background: var(--bg-surface-elevated);
            color: var(--text-main);
            border: 1px solid var(--border-color);
            font-weight: 500;
            font-size: 0.82rem;
            padding: 0.45rem 0.85rem;
            border-radius: var(--radius-sm);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            transition: all 0.2s ease;
        }}

        .btn-action-secondary:hover {{
            background: var(--bg-surface);
            border-color: var(--accent);
            color: var(--accent);
        }}

        .btn-copy {{
            background: transparent;
            color: var(--text-muted);
            border: 1px solid var(--border-color);
            font-size: 0.8rem;
            padding: 0.45rem 0.65rem;
            border-radius: var(--radius-sm);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            transition: all 0.15s ease;
        }}

        .btn-copy:hover {{
            color: var(--text-main);
            border-color: var(--text-secondary);
        }}

        /* Source Badges with Brand Accent Colors */
        .badge-source {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            font-family: var(--font-mono);
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}

        .badge-hn {{
            background: rgba(255, 102, 0, 0.15);
            color: #ff7417;
            border: 1px solid rgba(255, 102, 0, 0.4);
        }}

        .badge-aws {{
            background: rgba(255, 153, 0, 0.15);
            color: #ff9900;
            border: 1px solid rgba(255, 153, 0, 0.4);
        }}

        .badge-github {{
            background: rgba(35, 134, 54, 0.18);
            color: #3fb950;
            border: 1px solid rgba(35, 134, 54, 0.45);
        }}

        .badge-gcp {{
            background: rgba(66, 133, 244, 0.18);
            color: #60a5fa;
            border: 1px solid rgba(66, 133, 244, 0.45);
        }}

        .badge-fowler {{
            background: rgba(14, 165, 233, 0.18);
            color: #38bdf8;
            border: 1px solid rgba(14, 165, 233, 0.45);
        }}

        .badge-default {{
            background: rgba(129, 140, 248, 0.15);
            color: #a5b4fc;
            border: 1px solid rgba(129, 140, 248, 0.35);
        }}

        .read-time-pill {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--text-muted);
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
        }}

        /* TL;DR Callout Box */
        .tldr-quote {{
            margin: 1rem 0;
            padding: 1rem 1.25rem;
            background: var(--tldr-bg);
            border-left: 4px solid var(--tldr-border);
            border-radius: 0 var(--radius-md) var(--radius-md) 0;
            position: relative;
        }}

        .tldr-label {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.35rem;
        }}

        .tldr-text {{
            font-size: 0.95rem;
            font-weight: 500;
            color: var(--text-main);
            line-height: 1.6;
        }}

        .insight-quote {{
            background: rgba(129, 140, 248, 0.08);
            border-left-color: #818cf8;
        }}

        .insight-quote .tldr-label {{
            color: #818cf8;
        }}

        .standard-quote {{
            margin: 0.85rem 0;
            padding: 0.75rem 1rem;
            background: var(--bg-surface);
            border-left: 3px solid var(--border-color);
            border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
            font-style: italic;
            color: var(--text-secondary);
            font-size: 0.92rem;
            line-height: 1.6;
        }}

        /* Styled Lists */
        .styled-list, .styled-ordered-list {{
            list-style: none;
            margin: 0.85rem 0;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}

        .styled-list li {{
            display: flex;
            align-items: baseline;
            gap: 0.6rem;
            font-size: 0.94rem;
            color: var(--text-secondary);
            line-height: 1.6;
        }}

        .bullet-icon {{
            color: var(--accent);
            font-size: 0.85rem;
            flex-shrink: 0;
        }}

        .divider, .section-divider {{
            border: 0;
            border-top: 1px solid var(--border-color);
            margin: 1.75rem 0;
        }}

        /* Links & Code */
        a.ext-link {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 600;
            transition: color 0.15s ease;
        }}

        a.ext-link:hover {{
            color: var(--accent-hover);
            text-decoration: underline;
        }}

        .inline-code {{
            font-family: var(--font-mono);
            background: var(--bg-surface-elevated);
            color: var(--accent);
            padding: 0.15rem 0.35rem;
            border-radius: 4px;
            font-size: 0.85em;
            border: 1px solid var(--border-color);
        }}

        .code-block {{
            font-family: var(--font-mono);
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 1rem 1.25rem;
            font-size: 0.88rem;
            overflow-x: auto;
            margin: 1rem 0;
            color: #e2e8f0;
        }}

        .spinner {{
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top-color: #ffffff;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            display: inline-block;
        }}

        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}

        /* Footer */
        .app-footer {{
            border-top: 1px solid var(--border-color);
            padding: 1.5rem;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            font-family: var(--font-mono);
            margin-top: auto;
        }}
    </style>
</head>
<body>
    <!-- App Header -->
    <header class="app-header">
        <div class="header-container">
            <div class="brand-section">
                <div class="brand-icon">⚡</div>
                <div class="brand-meta">
                    <span class="brand-title">Personal Tech-Briefing Digest</span>
                    <span class="brand-subtitle">Cloud Run Instances Singleton • ADK 2.0 Engine</span>
                </div>
            </div>

            <div class="status-pills">
                <div class="pill pill-active">
                    <span class="dot"></span>
                    <span>Cloud Run Instance: Active</span>
                </div>
                <div class="pill pill-cost">
                    <span>$5.70/mo flat</span>
                </div>
            </div>

            <div class="header-actions">
                <button class="btn btn-icon-only" id="theme-toggle" title="Toggle Dark/Light Mode (Hotkey: t)" onclick="toggleTheme()">
                    <span id="theme-icon">🌙</span>
                </button>
                <button class="btn btn-primary" id="refresh-btn" onclick="triggerRefresh()">
                    <span id="refresh-icon">⚡</span>
                    <span id="refresh-text">Generate New Briefing</span>
                </button>
            </div>
        </div>
    </header>

    <!-- Floating Toast Notification -->
    <div id="notification-toast">
        <span id="toast-icon">✨</span>
        <span id="toast-msg">Notification</span>
    </div>

    <!-- Main Layout -->
    <div class="app-layout">
        <!-- Sidebar -->
        <aside class="app-sidebar">
            <!-- Search & Filters -->
            <div class="sidebar-card">
                <div class="sidebar-title">
                    <span>Quick Filter</span>
                    <span style="font-size:0.7rem;">Hotkey: /</span>
                </div>
                <div class="search-wrapper">
                    <span class="search-icon">🔍</span>
                    <input type="text" id="search-input" class="search-input" placeholder="Search topics, text, sources..." oninput="filterArticles()">
                    <span class="search-shortcut">/</span>
                </div>
                <div class="topic-filter-chips">
                    <button class="topic-chip active" onclick="filterByTopic('all', this)">All</button>
                    <button class="topic-chip" onclick="filterByTopic('AI', this)">AI</button>
                    <button class="topic-chip" onclick="filterByTopic('Cloud', this)">Cloud</button>
                    <button class="topic-chip" onclick="filterByTopic('Serverless', this)">Serverless</button>
                    <button class="topic-chip" onclick="filterByTopic('Systems', this)">Systems</button>
                    <button class="topic-chip" onclick="filterByTopic('Go', this)">Go</button>
                    <button class="topic-chip" onclick="filterByTopic('Python', this)">Python</button>
                </div>
            </div>

            <!-- Table of Contents -->
            <div class="sidebar-card">
                <div class="sidebar-title">Table of Contents</div>
                <ul class="toc-list" id="toc-container">
                    <!-- Populated dynamically via JS or server -->
                </ul>
            </div>

            <!-- Past Digests Archive Selector -->
            <div class="sidebar-card">
                <div class="sidebar-title">Digest Archive</div>
                <select id="archive-select" class="archive-select" onchange="loadArchiveDigest(this.value)">
                    <option value="latest">Latest Briefing</option>
                </select>
            </div>
        </aside>

        <!-- Main Content Area -->
        <main class="main-reader-content" id="reader-body">
            <div class="content-card">
                {body_html}
            </div>
        </main>
    </div>

    <!-- Footer -->
    <footer class="app-footer">
        Personal Tech-Briefing Digest • Google Cloud Run Instances (Singleton) • ADK 2.0 Graph Workflow
    </footer>

    <!-- Client-Side Enhancements & Micro-Interactions -->
    <script>
        // Theme Toggle Persistence
        function initTheme() {{
            const savedTheme = localStorage.getItem('digest-theme') || 'dark';
            document.documentElement.setAttribute('data-theme', savedTheme);
            document.getElementById('theme-icon').innerText = savedTheme === 'dark' ? '🌙' : '☀️';
        }}

        function toggleTheme() {{
            const current = document.documentElement.getAttribute('data-theme') || 'dark';
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('digest-theme', next);
            document.getElementById('theme-icon').innerText = next === 'dark' ? '🌙' : '☀️';
            showToast("Theme changed to " + next + " mode", "🎨");
        }}

        // Toast Feedback System
        function showToast(message, icon = "✨", duration = 3000) {{
            const toast = document.getElementById('notification-toast');
            document.getElementById('toast-msg').innerText = message;
            document.getElementById('toast-icon').innerText = icon;
            toast.classList.add('show');
            setTimeout(() => {{
                toast.classList.remove('show');
            }}, duration);
        }}

        // Copy Link to Clipboard
        function copyLink(url, btnElement) {{
            navigator.clipboard.writeText(url).then(() => {{
                if (btnElement) {{
                    const orig = btnElement.innerHTML;
                    btnElement.innerHTML = "✓ Copied!";
                    setTimeout(() => {{ btnElement.innerHTML = orig; }}, 2000);
                }}
                showToast("Link copied to clipboard!", "📋");
            }}).catch(err => {{
                showToast("Failed to copy link", "⚠️");
            }});
        }}

        // Real-time Search & Filter
        let currentTopic = 'all';
        function filterArticles() {{
            const query = (document.getElementById('search-input').value || '').toLowerCase();
            const cards = document.querySelectorAll('.content-card, .main-reader-content > div');
            
            cards.forEach(card => {{
                const text = card.innerText.toLowerCase();
                const matchesQuery = !query || text.includes(query);
                const matchesTopic = currentTopic === 'all' || text.includes(currentTopic.toLowerCase());
                
                if (matchesQuery && matchesTopic) {{
                    card.style.display = '';
                }} else if (card.querySelector('h2') || card.querySelector('h3')) {{
                    card.style.display = 'none';
                }}
            }});
        }}

        function filterByTopic(topic, btn) {{
            currentTopic = topic;
            document.querySelectorAll('.topic-chip').forEach(c => c.classList.remove('active'));
            if (btn) btn.classList.add('active');
            filterArticles();
            showToast("Filtered by topic: " + topic, "🏷️");
        }}

        // Dynamic Table of Contents Generation
        function buildTableOfContents() {{
            const tocContainer = document.getElementById('toc-container');
            tocContainer.innerHTML = '';
            
            const headings = document.querySelectorAll('.main-reader-content h2, .main-reader-content h3');
            let idx = 1;
            headings.forEach(h => {{
                const text = h.innerText.replace(/^[0-9]+[.]\\s*/, '').trim();
                if (!text || text.includes("Executive Summary") || text.includes("System Status")) return;
                
                // Ensure anchor ID
                if (!h.id) {{
                    h.id = 'heading-' + idx;
                }}
                
                const li = document.createElement('li');
                li.className = 'toc-item';
                li.innerHTML = `<a href="#${{h.id}}"><span class="toc-num">${{idx}}.</span><span>${{text.substring(0, 45)}}${{text.length > 45 ? '...' : ''}}</span></a>`;
                tocContainer.appendChild(li);
                idx++;
            }});

            if (tocContainer.children.length === 0) {{
                tocContainer.innerHTML = '<li class="toc-item" style="color:var(--text-muted);font-size:0.8rem;padding:0.4rem;">No jump links available</li>';
            }}
        }}

        // Fetch past digests archive
        async function fetchArchiveDigests() {{
            try {{
                const resp = await fetch('/api/digests');
                if (resp.ok) {{
                    const data = await resp.json();
                    const select = document.getElementById('archive-select');
                    data.digests.forEach(d => {{
                        const opt = document.createElement('option');
                        opt.value = d.filename;
                        opt.innerText = `${{d.date}} (${{Math.round(d.size_bytes / 1024)}} KB)`;
                        select.appendChild(opt);
                    }});
                }}
            }} catch (e) {{
                console.debug("Archive fetch skipped or offline", e);
            }}
        }}

        async function loadArchiveDigest(filename) {{
            if (filename === 'latest') {{
                window.location.href = '/digest/latest';
                return;
            }}
            try {{
                showToast("Loading archive " + filename + "...", "⏳");
                const resp = await fetch('/api/digest/' + filename);
                if (resp.ok) {{
                    const data = await resp.json();
                    // Reload page or display content
                    window.location.reload();
                }}
            }} catch (e) {{
                showToast("Failed loading archive: " + e, "⚠️");
            }}
        }}

        // Refresh / Generation Handler
        async function triggerRefresh() {{
            const btn = document.getElementById('refresh-btn');
            const icon = document.getElementById('refresh-icon');
            const text = document.getElementById('refresh-text');
            
            btn.disabled = true;
            icon.className = "spinner";
            icon.innerText = "";
            text.innerText = "Curating & Summarizing...";
            showToast("Agent pipeline executing across feeds...", "⚡", 6000);

            try {{
                const resp = await fetch('/api/generate', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ force_refresh: true }})
                }});

                if (resp.ok) {{
                    showToast("New briefing generated! Refreshing view...", "✅", 2000);
                    setTimeout(() => {{ window.location.reload(); }}, 1000);
                }} else {{
                    const err = await resp.json();
                    showToast("Generation failed: " + (err.detail || "Error"), "❌", 5000);
                    btn.disabled = false;
                    icon.className = "";
                    icon.innerText = "⚡";
                    text.innerText = "Generate New Briefing";
                }}
            }} catch (e) {{
                showToast("Network error: " + e, "❌", 5000);
                btn.disabled = false;
                icon.className = "";
                icon.innerText = "⚡";
                text.innerText = "Generate New Briefing";
            }}
        }}

        // Keyboard Shortcuts
        document.addEventListener('keydown', (e) => {{
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {{
                if (e.key === 'Escape') {{
                    e.target.blur();
                }}
                return;
            }}

            if (e.key === '/') {{
                e.preventDefault();
                const searchInput = document.getElementById('search-input');
                searchInput.focus();
                searchInput.select();
            }} else if (e.key === 't' || e.key === 'T') {{
                toggleTheme();
            }}
        }});

        // Enhance Source Badges with Brand Accent Styling
        function enhanceArticleCards() {{
            document.querySelectorAll('.main-reader-content h2').forEach(h2 => {{
                const text = h2.innerText;
                const nextEl = h2.nextElementSibling;
                
                // Add jump link icon & styling
                const jumpBtn = document.createElement('button');
                jumpBtn.className = 'btn-copy';
                jumpBtn.innerHTML = '📋 Copy';
                jumpBtn.onclick = () => {{
                    const link = h2.querySelector('a');
                    copyLink(link ? link.href : window.location.href, jumpBtn);
                }};
                h2.appendChild(jumpBtn);
            }});
        }}

        // Initialize on DOMContentLoaded
        document.addEventListener('DOMContentLoaded', () => {{
            initTheme();
            buildTableOfContents();
            fetchArchiveDigests();
            enhanceArticleCards();
        }});
    </script>
</body>
</html>
"""


async def _background_digest_loop() -> None:
    """Periodic background task that generates digests every POLL_INTERVAL_MINUTES.
    
    Cloud Run instances automatically restart up to every 7 days by default.
    The background loop handles this gracefully by operating as a resilient daemon
    that reads persisted state from /data and resumes its periodic schedule on startup.
    """
    interval_seconds = POLL_INTERVAL_MINUTES * 60
    logger.info("Starting background digest loop with interval %d minutes (7-day restart lifecycle resilient)", POLL_INTERVAL_MINUTES)

    while not _is_shutting_down:
        try:
            await asyncio.sleep(interval_seconds)
            if _is_shutting_down:
                break

            logger.info("Executing scheduled periodic digest workflow...")
            if not workflow_mutex.locked():
                async with workflow_mutex:
                    await execute_digest_workflow()
                    logger.info("Scheduled digest workflow completed successfully")
            else:
                logger.info("Workflow mutex locked; skipping scheduled run")
        except asyncio.CancelledError:
            logger.info("Background digest loop received cancellation (container restart or shutdown)")
            break
        except Exception as e:
            logger.error("Error in background digest loop: %s", e, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for background scheduler and graceful shutdown.
    
    Handles the Cloud Run 7-day automatic restart lifecycle:
    1. On Startup: Verifies directory structure and persistent GCS mount at /data,
       then initializes the background news aggregation scheduler.
    2. On SIGTERM / Shutdown: Traps SIGTERM sent during Cloud Run 7-day automatic container
       rotations, cancels the background loop cleanly, and allows any in-flight atomic file
       writes to complete safely before exit.
    """
    global _background_task, _is_shutting_down
    ensure_directories()
    logger.info("Starting up Personal Tech-Briefing Digest Service (Cloud Run Singleton Instance)")
    logger.info("Persistent storage initialized at: %s", DIGESTS_DIR.parent)

    # Set up SIGTERM handler for graceful state flush during 7-day instance rotation
    loop = asyncio.get_running_loop()

    def _handle_sigterm():
        global _is_shutting_down
        logger.info("SIGTERM received (Cloud Run automatic restart/rotation), initiating graceful shutdown")
        _is_shutting_down = True
        if _background_task and not _background_task.done():
            _background_task.cancel()

    try:
        loop.add_signal_handler(signal.SIGTERM, _handle_sigterm)
    except (NotImplementedError, RuntimeError):
        pass  # Signal handlers might not be supported on non-main threads or some OS configurations

    # Launch background scheduler
    _background_task = asyncio.create_task(_background_digest_loop())

    yield

    # Shutdown sequence
    _is_shutting_down = True
    if _background_task and not _background_task.done():
        _background_task.cancel()
        try:
            await _background_task
        except asyncio.CancelledError:
            pass

    logger.info("Personal Tech-Briefing Digest Service graceful shutdown complete")


app = FastAPI(
    title="Personal Tech-Briefing Digest Agent",
    description="Automated Daily Tech Briefing powered by Google ADK 2.0 on Cloud Run Instances",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
@app.get("/digest/latest", response_class=HTMLResponse)
async def get_latest_digest_view():
    """Render the latest digest as an HTML reading page."""
    latest_file = DIGESTS_DIR / "latest.md"
    if not latest_file.exists():
        # Look for any recent digest file
        digests = sorted(list(DIGESTS_DIR.glob("*-digest.md")), reverse=True)
        if digests:
            latest_file = digests[0]

    if not latest_file.exists():
        empty_md = (
            "# No Digests Available Yet\n\n"
            "The Personal Tech-Briefing Digest Agent has not generated any briefing yet.\n\n"
            "Click **Refresh Digest** above or call `POST /api/generate` to trigger the first briefing."
        )
        return HTMLResponse(content=_render_html_page("Tech Briefing - No Digest", empty_md))

    try:
        markdown_text = latest_file.read_text(encoding="utf-8")
        return HTMLResponse(content=_render_html_page("Personal Tech Briefing", markdown_text))
    except Exception as e:
        logger.error("Error reading latest digest: %s", e)
        raise HTTPException(status_code=500, detail="Failed to read latest digest file")


@app.get("/healthz")
async def health_check():
    """Cloud Run health check endpoint."""
    return {
        "status": "ok",
        "service": "digest-agent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage_ready": STATE_DIR.exists() and DIGESTS_DIR.exists(),
    }


@app.get("/api/digests")
async def list_digests():
    """Return list of all available digests on disk/GCS volume."""
    ensure_directories()
    digest_files = sorted(list(DIGESTS_DIR.glob("*-digest.md")), reverse=True)
    results = []

    for df in digest_files:
        try:
            stat = df.stat()
            results.append({
                "filename": df.name,
                "date": df.name.replace("-digest.md", ""),
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
        except Exception:
            continue

    return {"digests": results, "total": len(results)}


@app.get("/api/digest/{filename}")
async def get_digest(filename: str):
    """Retrieve raw markdown content for a specific digest file."""
    # Sanitize filename
    safe_name = Path(filename).name
    if not safe_name.endswith(".md"):
        safe_name = f"{safe_name}.md"

    target = DIGESTS_DIR / safe_name
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Digest file not found")

    try:
        content = target.read_text(encoding="utf-8")
        return {
            "filename": safe_name,
            "markdown_content": content,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed reading file: {e}")


@app.post("/api/generate")
async def generate_digest_endpoint(payload: GenerateRequest | None = None):
    """Trigger on-demand digest generation guarded by the workflow execution mutex."""
    if workflow_mutex.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Digest generation is already in progress. Please wait for the current run to finish."
        )

    req = payload or GenerateRequest()
    interests = UserInterests(
        topics=req.topics or [],
        max_articles=req.max_articles,
    ) if req.topics else None

    async with workflow_mutex:
        try:
            digest: DailyDigest = await execute_digest_workflow(
                interests=interests,
                feeds=req.feeds,
                force_refresh=req.force_refresh,
            )
            return {
                "status": "success",
                "title": digest.title,
                "date": digest.date,
                "articles_summarized": len(digest.summaries),
                "markdown_length": len(digest.markdown_content),
            }
        except Exception as e:
            logger.error("Manual digest generation failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Workflow execution failed: {e}")


@app.post("/api/webhook")
async def handle_incoming_webhook(
    payload: WebhookPayload,
    x_agent_secret: str | None = Header(default=None, alias="X-Agent-Secret"),
):
    """Accept real-time incoming alerts (e.g. tweet notifications, GitHub releases, iOS Shortcuts)
    and immediately extract, summarize, and incorporate them into the active briefing."""
    if WEBHOOK_SECRET and x_agent_secret != WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Agent-Secret header"
        )

    if not payload.url and not payload.text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 'url' or 'text' must be provided in the webhook payload."
        )

    async with workflow_mutex:
        try:
            summary = await summarize_single_alert(
                url=payload.url,
                text=payload.text,
                title=payload.title,
                author=payload.author,
                source=payload.source,
            )

            # Record seen URL if provided
            if payload.url:
                record_seen_urls(SEEN_URLS_FILE, [payload.url], RETENTION_DAYS)

            # Atomically update latest.md and date digest
            ensure_directories()
            latest_file = DIGESTS_DIR / "latest.md"
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            today_file = DIGESTS_DIR / f"{today_str}-digest.md"

            card_md = f"\n\n### [{summary.title}]({summary.url})\n"
            card_md += f"**Source:** {summary.source} • **Read time:** {summary.read_time}\n\n"
            card_md += f"**TL;DR:** {summary.tldr}\n"
            if summary.key_takeaways:
                card_md += "\n**Key Technical Takeaways:**\n"
                for t in summary.key_takeaways:
                    card_md += f"- {t}\n"

            if latest_file.exists():
                existing = latest_file.read_text(encoding="utf-8")
                if "## Curated Articles" in existing:
                    parts = existing.split("## Curated Articles", 1)
                    new_content = parts[0] + "## Curated Articles" + card_md + parts[1]
                else:
                    new_content = existing + "\n\n## Real-Time Alerts" + card_md
            else:
                new_content = f"# Personal Tech Briefing — {today_str}\n\n## Curated Articles" + card_md

            atomic_save_text(latest_file, new_content)
            atomic_save_text(today_file, new_content)

            return {
                "status": "success",
                "message": f"Successfully processed {payload.source} alert",
                "summary": {
                    "title": summary.title,
                    "url": summary.url,
                    "source": summary.source,
                    "tldr": summary.tldr,
                    "key_takeaways": summary.key_takeaways,
                    "quality_score": summary.quality_score,
                }
            }
        except Exception as e:
            logger.error("Webhook alert processing failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed processing alert: {e}")

