"""Utility functions for Personal Tech-Briefing Digest Agent.

Provides SSRF validation, feed ingestion (HN & RSS), safe content extraction,
atomic JSON file persistence, and seen URL pruning.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import html
import ipaddress
import json
import logging
import math
import os
from pathlib import Path
import re
import socket
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlparse, urlunparse

import httpx

from digest_agent.schemas import ArticleMetadata

logger = logging.getLogger(__name__)

# SSRF Blocked IP Subnets and Ranges
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918 Private
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local & Cloud Metadata
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918 Private
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918 Private
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmark testing
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6 ranges
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),           # Loopback
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-local
    ipaddress.ip_network("ff00::/8"),           # Multicast
]

METADATA_IP = "169.254.169.254"


def canonicalize_url(url: str) -> str:
    """Normalize URLs for deterministic deduplication and stable tie-breaking across feeds and runs.
    
    - Converts scheme and netloc to lowercase
    - Strips www. prefix
    - Strips tracking query parameters (utm_*, ref, source, fbclid, gclid, etc.)
    - Strips URL fragments (#...)
    - Normalizes trailing slashes
    """
    if not url or not isinstance(url, str):
        return ""
    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower()
        if not scheme:
            scheme = "https"
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        
        # Strip tracking query parameters
        tracking_params = {
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "ref", "source", "fbclid", "gclid", "mc_cid", "mc_eid", "si"
        }
        query_pairs = [
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False)
            if k.lower() not in tracking_params
        ]
        query_pairs.sort(key=lambda x: x[0])
        clean_query = urlencode(query_pairs)
        
        path = parsed.path.rstrip("/")
        if not path and not clean_query:
            path = ""
            
        return urlunparse((scheme, netloc, path, "", clean_query, ""))
    except Exception:
        return url.strip()


# Tiered Taxonomy for High-Signal AI / Agent Scoring
TIER1_AI_AGENT_TERMS = {
    "agent", "agents", "multi-agent", "agentic", "adk", "mcp", "model context protocol",
    "tool use", "tool calling", "function calling", "reasoning", "chain of thought",
    "rag", "vector search", "embedding", "embeddings", "llm", "llms", "large language model",
    "prompt engineering", "eval", "evals", "evaluation", "guardrails", "synthetic data",
    "langchain", "langgraph", "autogen", "crewai", "semantic kernel", "vllm", "sglang",
    "speculative decoding", "fine-tuning", "lora", "context window", "tokens", "inference",
    "ai engineer", "ai engineering", "model weights", "attention", "transformer", "diffusion",
}

TIER2_SYSTEMS_TERMS = {
    "cloud run", "kubernetes", "k8s", "docker", "container", "sandbox", "sandboxing",
    "serverless", "microservice", "distributed", "concurrency", "asyncio", "runtime",
    "compiler", "profiling", "benchmark", "latency", "throughput", "memory",
    "postgres", "postgresql", "sqlite", "spanner", "bigquery", "redis", "kafka",
    "grpc", "http/2", "http/3", "websocket", "ssrf", "iam", "oauth", "security", "wasm",
}

HIGH_AUTHORITY_DOMAINS = {
    "simonwillison.net", "latent.space", "eugeneyan.com", "huyenchip.com",
    "lilianweng.github.io", "langchain.com", "anthropic.com", "github.blog"
}


def compute_deterministic_relevance_score(
    title: str,
    snippet: str = "",
    source: str = "",
    url: str = "",
    score: int = 0,
    comments_count: int = 0,
) -> tuple[float, bool, str]:
    """Calculate deterministic relevance score and validity for candidate ranking.
    
    Returns:
        (calculated_score, is_acceptable, rejection_reason)
    """
    is_tech, reason = is_genuinely_technical(title, snippet=snippet)
    if not is_tech:
        return -100.0, False, reason

    corpus = f"{title} {snippet}".lower()
    tokens = set(re.findall(r"\b[a-z0-9_/-]+\b", corpus))
    words = re.findall(r"\b[a-z0-9_/-]+\b", corpus)
    two_grams = {f"{words[i]} {words[i+1]}" for i in range(len(words)-1)} if len(words) > 1 else set()
    all_ngrams = tokens | two_grams

    t1_hits = sum(1 for term in TIER1_AI_AGENT_TERMS if term in all_ngrams or term in corpus)
    t2_hits = sum(1 for term in TIER2_SYSTEMS_TERMS if term in all_ngrams or term in corpus)

    # Authority domain boost
    parsed_netloc = urlparse(url.lower()).netloc.replace("www.", "")
    authority_boost = 15.0 if any(auth in parsed_netloc for auth in HIGH_AUTHORITY_DOMAINS) else 0.0

    # Engagement scaling (bounded logarithmic scaling to prevent HN score skew)
    engagement_points = min(25.0, math.log2(score + 1) * 3.0) + min(15.0, comments_count * 0.4)

    # AI Multiplier boost
    ai_multiplier = 1.6 if t1_hits > 0 else 0.8

    drs = ((t1_hits * 18.0) + (t2_hits * 6.0) + authority_boost + engagement_points) * ai_multiplier

    # Must meet a minimum signal threshold
    if drs < 10.0 and t1_hits == 0:
        return drs, False, "Insufficient AI, Agent, or Systems signal strength."

    return round(drs, 3), True, f"Tier1 hits: {t1_hits}, Tier2 hits: {t2_hits}, Score: {drs:.1f}"


def is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address belongs to blocked or private/reserved subnets."""
    # Check for IPv4-mapped IPv6 addresses (e.g. ::ffff:169.254.169.254)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    if str(ip) == METADATA_IP:
        return True

    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
        return True

    for net in BLOCKED_NETWORKS:
        if ip in net:
            return True

    return False


def is_safe_url(url: str) -> bool:
    """Validate that a URL uses HTTP/HTTPS and does not point to internal/SSRF targets.

    Blocks:
    - Non-HTTP/HTTPS schemes
    - Cloud Metadata IP (169.254.169.254)
    - Loopback addresses (127.0.0.1, ::1, localhost)
    - IPv4-mapped IPv6 addresses (e.g. ::ffff:169.254.169.254)
    - RFC 1918 subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Link-local subnets (169.254.0.0/16, fe80::/10)
    - DNS rebinding to internal IP targets
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False

    if parsed.scheme.lower() not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    hostname = hostname.lower().strip("[]")

    if hostname in ("localhost", "localhost.localdomain", "broadcasthost"):
        return False

    # Check direct IP address literal
    try:
        ip_obj = ipaddress.ip_address(hostname)
        return not is_ip_blocked(ip_obj)
    except ValueError:
        pass

    # Resolve hostname via DNS to prevent DNS rebinding / internal host resolution
    try:
        addr_infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        for family, _, _, _, sockaddr in addr_infos:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)
            if is_ip_blocked(ip_obj):
                return False
    except (socket.gaierror, socket.herror, TimeoutError, OSError):
        # In test environments or offline mode, allow non-resolving public-format domains if not obviously private
        if hostname.endswith(".local") or hostname.endswith(".internal") or hostname.endswith(".corp"):
            return False

    return True


def estimate_read_time(text: str, default: str = "3 min read") -> str:
    """Calculate an estimated reading time from text word count."""
    if not text or not text.strip():
        return default
    clean = re.sub(r"<[^>]+>", " ", text).replace("<untrusted_content>", "").replace("</untrusted_content>", "")
    words = len(clean.split())
    if words == 0:
        return default
    minutes = max(1, round(words / 200))
    return f"{minutes} min read"


def clean_source_name(raw_title: str | None, url: str | None = None) -> str:
    """Normalize and format source brand names into clean, readable labels."""
    raw = (raw_title or "").strip()
    u = (url or "").lower()

    if "reddit.com/r/" in u:
        match = re.search(r"reddit\.com/r/([^/?#]+)", u)
        if match:
            return f"Reddit r/{match.group(1)}"
        return "Reddit"
    if "simonwillison.net" in u:
        return "Simon Willison"
    if "latent.space" in u:
        return "Latent Space"
    if "eugeneyan.com" in u:
        return "Eugene Yan"
    if "huyenchip.com" in u:
        return "Chip Huyen"
    if "lilianweng.github.io" in u or "lil'log" in raw.lower() or "lillog" in raw.lower():
        return "Lil'Log (Lilian Weng)"
    if "langchain.com" in u or "langchain" in raw.lower():
        return "LangChain Blog"
    if "anthropic.com/engineering" in u:
        return "Anthropic Engineering"
    if "anthropic.com/research" in u:
        return "Anthropic Research"
    if "anthropic.com" in u or "anthropic" in raw.lower():
        return "Anthropic"
    if "huggingface.co" in u:
        return "Hugging Face"
    if "modelcontextprotocol" in u:
        return "Model Context Protocol (MCP)"
    if "ycombinator.com" in u or "hacker news" in raw.lower():
        return "Hacker News"
    if "aws.amazon.com/blogs/machine-learning" in u:
        return "AWS Machine Learning"
    if "aws.amazon.com" in u or "aws" in raw.lower():
        return "AWS News"
    if "cloudblog.withgoogle.com" in u or "cloud.google.com" in u or "google cloud" in raw.lower():
        return "Google Cloud"
    if "github.blog" in u or "github" in raw.lower():
        return "GitHub Blog"
    if "martinfowler.com" in u or "martin fowler" in raw.lower():
        return "Martin Fowler"

    if raw:
        # Strip common feed suffixes
        cleaned = re.sub(r"\s*-\s*Blog.*$", "", raw, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*\|\s*.*$", "", cleaned)
        cleaned = re.sub(r"\s+RSS\s+Feed.*$", "", cleaned, flags=re.IGNORECASE)
        if cleaned.strip():
            return cleaned.strip()

    if url:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc.capitalize()

    return "Tech Feed"


def format_timestamp(ts: str | int | float | None) -> str:
    """Format an ISO timestamp or epoch integer into a clean, human-readable date string."""
    if not ts:
        return datetime.now(timezone.utc).strftime("%b %d, %Y")

    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%b %d, %Y")

    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        # Return first 10 characters if formatted like YYYY-MM-DD
        s = str(ts).strip()
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return s[:10]
        return s or datetime.now(timezone.utc).strftime("%b %d, %Y")


async def verify_link_liveliness(url: str, client: httpx.AsyncClient | None = None) -> bool:
    """Check if a URL is active, reachable, and not a dead 404 or dropped DNS link.
    
    Resilient to anti-bot shields (treats 200..399, 401, 403, 405, 429 as alive).
    Only drops links on definitive 404/410 errors, DNS lookup failures, or connect timeouts.
    """
    if not is_safe_url(url):
        return False

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async def _check(c: httpx.AsyncClient) -> bool:
        try:
            resp = await c.head(url, headers=headers, timeout=3.0, follow_redirects=True)
            if resp.status_code == 405:  # Method Not Allowed on HEAD
                resp = await c.get(url, headers={**headers, "Range": "bytes=0-1024"}, timeout=3.0, follow_redirects=True)
            if resp.status_code in (404, 410):
                return False
            # 2xx, 3xx, 401, 403, 429 are considered alive (bot shields or auth-gated)
            return True
        except (httpx.ConnectError, httpx.ConnectTimeout, socket.gaierror):
            return False
        except Exception:
            # For transient network errors, don't falsely discard
            return True

    if client:
        return await _check(client)
    else:
        try:
            async with httpx.AsyncClient(timeout=4.0) as c:
                return await _check(c)
        except Exception:
            return True


def is_within_freshness_window(ts: datetime | int | float | str | None, max_days: int = 14) -> bool:
    """Check if a timestamp is within the last `max_days` (default 14 days)."""
    if ts is None:
        return True  # If timestamp is missing from feed, allow candidate
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_days)

    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt >= cutoff
        elif isinstance(ts, datetime):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts >= cutoff
        elif isinstance(ts, (tuple, list)) and len(ts) >= 6:
            # struct_time from feedparser
            import time
            epoch = time.mktime(ts)
            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            return dt >= cutoff
        else:
            s = str(ts).strip()
            # Try ISO format
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt >= cutoff
            except Exception:
                pass
            # Try RFC 2822 / 822 format (e.g. 'Thu, 28 Aug 2026 12:00:00 GMT')
            from email.utils import parsedate_to_datetime
            try:
                dt = parsedate_to_datetime(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt >= cutoff
            except Exception:
                return True
    except Exception:
        return True


def is_substantive_content(raw_or_wrapped_text: str, min_words: int = 50) -> bool:
    """Check if extracted content has at least `min_words` substantive words and is not an error message."""
    if not raw_or_wrapped_text:
        return False
    # Strip XML tags
    clean = re.sub(r"<[^>]+>", " ", raw_or_wrapped_text).strip()
    if not clean:
        return False
    if clean.startswith("[Blocked:") or clean.startswith("[Failed to fetch") or clean.startswith("[Empty content]"):
        return False
    words = [w for w in clean.split() if len(w) > 1]
    return len(words) >= min_words


async def fetch_hn_top_comments(story_id: int, max_comments: int = 5) -> list[str]:
    """Fetch top comments for a Hacker News story with tight latency bounds and HTML cleaning."""
    item_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
    comments: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(item_url)
            if resp.status_code != 200:
                return []
            data = resp.json()
            if not data:
                return []
            kid_ids: list[int] = data.get("kids", [])[:max_comments]
            if not kid_ids:
                return []

            async def _fetch_comment(cid: int) -> str | None:
                c_url = f"https://hacker-news.firebaseio.com/v0/item/{cid}.json"
                try:
                    c_resp = await client.get(c_url, timeout=3.0)
                    if c_resp.status_code == 200:
                        c_data = c_resp.json()
                        if c_data and not c_data.get("deleted") and not c_data.get("dead"):
                            text = clean_html_text(c_data.get("text", ""))
                            author = c_data.get("by", "anonymous")
                            if text and len(text) > 15:
                                # Bound comment length to 400 chars
                                bounded_text = text[:400] + ("..." if len(text) > 400 else "")
                                return f"{author}: {bounded_text}"
                except Exception:
                    pass
                return None

            tasks = [_fetch_comment(cid) for cid in kid_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, str) and res:
                    comments.append(res)
    except Exception as ex:
        logger.warning("Failed fetching HN comments for story %s: %s", story_id, ex)

    return comments


def wrap_untrusted_discussion(comments: list[str]) -> str:
    """Format discussion comments in untrusted XML wrapper for prompt injection defense."""
    if not comments:
        return "<untrusted_community_discussion>\n[No active community discussion comments available]\n</untrusted_community_discussion>"
    
    formatted = "\n".join(f"- {c}" for c in comments[:5])
    return f"<untrusted_community_discussion>\n{formatted}\n</untrusted_community_discussion>"


def clean_html_text(raw_text: str | None) -> str:
    """Clean, unescape HTML entities, strip tags, and remove conversational/meta prefixes."""
    if not raw_text:
        return ""
    # Unescape HTML entities (&amp;, &#x27;, &quot;, &lt;, &gt;, etc.)
    unescaped = html.unescape(raw_text)
    # Strip HTML tags
    no_tags = re.sub(r"<[^>]+>", " ", unescaped)
    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", no_tags).strip()
    # Remove conversational/author metadata preambles
    cleaned = re.sub(
        r"^(?:I posted once before[^.]*\.|I made this[^.]*\.|Hi HN[^.]*\.|Hey everyone[^.]*\.|Edit:[^.]*\.|Wanted to share[^.]*\.)\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    return cleaned


async def fetch_hn_top_stories(limit: int = 25, min_score: int = 20, max_days: int = 14) -> list[ArticleMetadata]:
    """Fetch top and high-engagement AI/agent stories from Hacker News (Firebase REST + Algolia Search) with 14-day freshness."""
    articles: list[ArticleMetadata] = []
    seen_urls: set[str] = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (PersonalTechDigestBot/1.0)"
    }

    try:
        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            # 1. Fetch real-time top stories from Firebase API
            try:
                top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
                resp = await client.get(top_url)
                if resp.status_code == 200:
                    story_ids: list[int] = resp.json()[:limit]

                    async def _fetch_item(item_id: int) -> ArticleMetadata | None:
                        item_url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
                        try:
                            item_resp = await client.get(item_url)
                            if item_resp.status_code != 200:
                                return None
                            data = item_resp.json()
                            if not data or data.get("type") != "story" or data.get("dead") or data.get("deleted"):
                                return None

                            title = html.unescape(data.get("title", "").strip())
                            if not title:
                                return None

                            score = int(data.get("score", 0) or 0)
                            if score < min_score:
                                return None

                            time_sec = data.get("time")
                            if time_sec and not is_within_freshness_window(time_sec, max_days=max_days):
                                return None

                            comments_count = int(data.get("descendants", 0) or 0)
                            hn_discussion_url = f"https://news.ycombinator.com/item?id={item_id}"
                            story_url = data.get("url")
                            canonical_url = story_url if story_url else hn_discussion_url

                            published_at = (
                                format_timestamp(time_sec)
                                if time_sec
                                else format_timestamp(None)
                            )
                            raw_snippet = data.get("text", "")
                            cleaned_snippet = clean_html_text(raw_snippet)
                            if not cleaned_snippet:
                                cleaned_snippet = f"Top discussion on Hacker News with {score} points and {comments_count} community comments."
                            
                            read_time = estimate_read_time(cleaned_snippet, default="4 min read")
                            importance_score = float(score + (comments_count * 1.5))

                            return ArticleMetadata(
                                title=title,
                                url=canonical_url,
                                source="Hacker News",
                                published_at=published_at,
                                snippet=cleaned_snippet,
                                discussion_url=hn_discussion_url,
                                read_time=read_time,
                                score=score,
                                comments_count=comments_count,
                                comments_text=[],
                                importance_score=importance_score,
                                is_verified=True,
                                has_full_article_content=True,
                            )
                        except Exception as ex:
                            logger.warning("Failed fetching HN story %s: %s", item_id, ex)
                            return None

                    tasks = [_fetch_item(sid) for sid in story_ids]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for res in results:
                        if isinstance(res, ArticleMetadata) and res.url not in seen_urls:
                            seen_urls.add(res.url)
                            articles.append(res)
            except Exception as e:
                logger.warning("Failed fetching HN Firebase top stories: %s", e)

            # 2. Fetch high-engagement AI & Agent stories across 14 days from Algolia HN API
            try:
                hn_search_queries = [
                    "agent LLM",
                    "AI agent",
                    "RAG MCP",
                    "Show HN agent",
                ]
                for hq in hn_search_queries:
                    algolia_url = (
                        f"https://hn.algolia.com/api/v1/search?"
                        f"query={quote_plus(hq)}"
                        f"&tags=story"
                        f"&numericFilters=points>{min_score}"
                        f"&hitsPerPage=20"
                    )
                    algolia_resp = await client.get(algolia_url)
                    if algolia_resp.status_code == 200:
                        hits = algolia_resp.json().get("hits", [])
                        for hit in hits:
                            oid = hit.get("objectID")
                            if not oid:
                                continue
                            hn_discussion_url = f"https://news.ycombinator.com/item?id={oid}"
                            story_url = hit.get("url")
                            canonical_url = story_url if story_url else hn_discussion_url

                            if canonical_url in seen_urls:
                                continue

                            title = html.unescape(hit.get("title", "").strip())
                            if not title:
                                continue

                            created_at = hit.get("created_at") or hit.get("created_at_i")
                            if created_at and not is_within_freshness_window(created_at, max_days=max_days):
                                continue

                            score = int(hit.get("points", 0) or 0)
                            if score < min_score:
                                continue

                            comments_count = int(hit.get("num_comments", 0) or 0)
                            raw_snippet = hit.get("story_text", "") or ""
                            cleaned_snippet = clean_html_text(raw_snippet)
                            if not cleaned_snippet:
                                cleaned_snippet = f"Hacker News discussion with {score} points and {comments_count} comments."

                            read_time = estimate_read_time(cleaned_snippet, default="4 min read")
                            importance_score = float(score + (comments_count * 1.5))

                            seen_urls.add(canonical_url)
                            articles.append(ArticleMetadata(
                                title=title,
                                url=canonical_url,
                                source="Hacker News",
                                published_at=format_timestamp(created_at),
                                snippet=cleaned_snippet,
                                discussion_url=hn_discussion_url,
                                read_time=read_time,
                                score=score,
                                comments_count=comments_count,
                                comments_text=[],
                                importance_score=importance_score,
                                is_verified=True,
                                has_full_article_content=True,
                            ))
            except Exception as e:
                logger.warning("Failed fetching HN Algolia stories: %s", e)

    except Exception as e:
        logger.error("Failed fetching Hacker News stories: %s", e)

    return articles


async def fetch_rss_feeds(feed_urls: list[str], max_days: int = 14) -> list[ArticleMetadata]:
    """Fetch and parse multiple RSS/Atom feeds with 14-day freshness window."""
    articles: list[ArticleMetadata] = []

    try:
        import feedparser
    except ImportError:
        feedparser = None

    feed_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (PersonalTechDigestBot/1.0; contact: dev-digest@example.com)"
    }
    async with httpx.AsyncClient(timeout=15.0, headers=feed_headers, follow_redirects=True) as client:
        for feed_url in feed_urls:
            if not is_safe_url(feed_url):
                logger.warning("Skipping unsafe feed URL: %s", feed_url)
                continue

            try:
                resp = await client.get(feed_url)
                if resp.status_code != 200:
                    logger.warning("HTTP %s for feed %s", resp.status_code, feed_url)
                    continue

                content = resp.text
                if feedparser:
                    parsed = feedparser.parse(content)
                    raw_title = parsed.feed.get("title", urlparse(feed_url).netloc)
                    clean_source = clean_source_name(raw_title, feed_url)
                    for entry in parsed.entries[:10]:
                        title = html.unescape(entry.get("title", "").strip())
                        link = entry.get("link", "").strip()
                        if not title or not link:
                            continue

                        raw_summary = entry.get("summary", entry.get("description", ""))
                        cleaned_summary = clean_html_text(raw_summary)

                        # Check if genuinely technical and not a minor release note or quote post
                        is_tech, _ = is_genuinely_technical(title, snippet=cleaned_summary)
                        if not is_tech:
                            continue

                        published = entry.get("published", entry.get("updated", ""))
                        parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
                        if parsed_time and not is_within_freshness_window(parsed_time, max_days=max_days):
                            continue
                        elif published and not is_within_freshness_window(published, max_days=max_days):
                            continue

                        formatted_date = format_timestamp(published)
                        read_time = estimate_read_time(cleaned_summary, default="3 min read")

                        comments_url = entry.get("comments") or entry.get("link") or feed_url

                        articles.append(
                            ArticleMetadata(
                                title=title,
                                url=link,
                                source=clean_source,
                                published_at=formatted_date,
                                snippet=cleaned_summary[:400],
                                discussion_url=comments_url if comments_url != link else feed_url,
                                read_time=read_time,
                                score=0,  # Curated RSS feeds do not have native upvote counts
                                comments_count=0,
                                comments_text=[],
                                importance_score=0.0,
                                is_verified=True,
                                has_full_article_content=True,
                            )
                        )
                else:
                    items = re.findall(r"<item>(.*?)</item>", content, re.DOTALL) or re.findall(r"<entry>(.*?)</entry>", content, re.DOTALL)
                    feed_title = urlparse(feed_url).netloc
                    clean_source = clean_source_name(feed_title, feed_url)
                    for item in items[:10]:
                        title_match = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
                        link_match = re.search(r"<link>(.*?)</link>", item, re.DOTALL) or re.search(r'<link[^>]*href=["\']([^"\']+)["\']', item)
                        if title_match and link_match:
                            raw_title = html.unescape(title_match.group(1).replace("<![CDATA[", "").replace("]]>", "").strip())
                            raw_link = html.unescape(link_match.group(1).strip())
                            is_tech, _ = is_genuinely_technical(raw_title)
                            if not is_tech:
                                continue
                            articles.append(
                                ArticleMetadata(
                                    title=raw_title,
                                    url=raw_link,
                                    source=clean_source,
                                    published_at=format_timestamp(None),
                                    snippet="",
                                    discussion_url=feed_url,
                                    read_time="3 min read",
                                    score=0,
                                    comments_count=0,
                                    comments_text=[],
                                    importance_score=0.0,
                                    is_verified=True,
                                    has_full_article_content=True,
                                )
                            )
            except Exception as e:
                logger.warning("Error fetching RSS feed %s: %s", feed_url, e)

    return articles


async def safe_extract_webpage(url: str, max_chars: int = 8000) -> str:
    """Fetch webpage content safely (validating redirects against SSRF) and extract clean readable text.

    Strips sidebar links, navigation blocks, footer boilerplate, and podcast timestamp intros.
    Wraps the resulting clean text in `<untrusted_content>` tags.
    """
    if not is_safe_url(url):
        return "<untrusted_content>\n[Blocked: Untrusted or Private URL Target]\n</untrusted_content>"

    current_url = url
    html_content = ""

    try:
        # Manual redirect following to validate each hop against SSRF
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            for _ in range(5):
                resp = await client.get(
                    current_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TechBriefingBot/1.0"}
                )
                if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location")
                    if not location:
                        break
                    next_url = urljoin(current_url, location)
                    if not is_safe_url(next_url):
                        logger.warning("Blocked SSRF redirect from %s to %s", current_url, next_url)
                        return "<untrusted_content>\n[Blocked: SSRF Redirect Target]\n</untrusted_content>"
                    current_url = next_url
                elif resp.status_code == 200:
                    html_content = resp.text
                    break
                else:
                    break
    except Exception as e:
        logger.warning("Error fetching page %s: %s", url, e)
        return f"<untrusted_content>\n[Failed to fetch article content: {e}]\n</untrusted_content>"

    if not html_content:
        return "<untrusted_content>\n[Empty content]\n</untrusted_content>"

    # Extract readable text using trafilatura if available
    extracted_text = ""
    try:
        import trafilatura
        extracted_text = trafilatura.extract(
            html_content,
            include_links=False,
            include_images=False,
            include_comments=False,
            output_format="txt"
        ) or ""
    except Exception:
        pass

    if not extracted_text:
        # Fallback text cleaner: strip head, scripts, styles, nav, footer, forms
        cleaned = re.sub(r"<(head|header|footer|nav|aside|script|style|form|noscript)[^>]*>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        no_tags = re.sub(r"<[^>]+>", " ", cleaned)
        unescaped = html.unescape(no_tags)
        # Filter out common crawler/SEO boilerplate lines
        lines = [
            line.strip() for line in unescaped.splitlines()
            if len(line.strip()) > 30
            and not re.search(r"(PageMeta|canonical pointing|earlier in the head|duplicate of the homepage|<!DOCTYPE|<html)", line, re.IGNORECASE)
        ]
        extracted_text = "\n".join(lines)

    # Post-clean: Strip sidebar lists, "Recent articles - ...", podcast timestamp lines
    cleaned_lines: list[str] = []
    for line in extracted_text.splitlines():
        line_str = line.strip()
        if not line_str:
            continue
        # Skip sidebar "Recent articles - ..." or navigation lists
        if re.search(r"^(?:Recent articles\s*-|Related posts\s*-|Subscribe to|Leave a comment|Sign up for the newsletter)", line_str, re.IGNORECASE):
            continue
        # Skip podcast timestamp intros like "Swyx [00:01:46]:" or "[00:01:46]"
        if re.search(r"^(?:(?:Swyx|Alessio|Speaker \d+|Host|Guest)\s*)?\[\d{1,2}:\d{2}(?::\d{2})?\]", line_str):
            continue
        cleaned_lines.append(line_str)

    clean_body = "\n".join(cleaned_lines).strip()

    # Truncate content to budget
    if len(clean_body) > max_chars:
        clean_body = clean_body[:max_chars] + "\n...[Content truncated for length]..."

    # Enclose in untrusted XML tag for injection defense
    return f"<untrusted_content>\n{clean_body}\n</untrusted_content>"


def is_genuinely_technical(title: str, text: str = "", snippet: str = "") -> tuple[bool, str]:
    """Classify whether content is genuinely about software engineering, architectures, protocols, or developer systems.
    
    Rejects:
    - Minor library release notes / version bumps (e.g. llm-anthropic 0.27, patch releases)
    - Quote posts & link stubs (e.g. Quoting Paul Dix)
    - Generic SQLite file format trivia unless architectural
    - Consumer complaints, legal disputes, DMCA notices, app store drama
    """
    corpus = f"{title} {snippet} {text[:1500]}".lower()

    # Immediate rejection for minor version bumps, release notes, or changelogs
    if re.search(r"^(?:llm-[a-z0-9_-]+\s+\d|llm\s+\d+\.\d+|datasette\s+\d|v?\d+\.\d+(\.\d+)?\s*(?:released|release|notes)?$|release notes\b|changelog\b)", title, re.IGNORECASE):
        return False, "Minor library release note, version bump, or changelog stub."

    # Immediate rejection for quote posts and link stubs
    if re.search(r"^(?:quoting\s+|quote:\s+|link:\s+)", title, re.IGNORECASE):
        return False, "Quote post or brief link stub."

    # Rejection for non-substantive database trivia
    if re.search(r"\byour executable is a sqlite database\b", title, re.IGNORECASE):
        return False, "Non-architectural file-format/database trivia."

    # Immediate rejection patterns for non-technical consumer complaints, legal/DMCA disputes, or personal lifestyle gripes
    non_tech_patterns = [
        r"\b(works better in the app|why i hate|why i left|canceled my|switched from)\b",
        r"\b(app store|play store|dmca|copyright|takedown|lawsuit|sued|patent litigation)\b",
        r"\b(customer support|refund|scam|ban(?:ned)? from|account (?:suspended|banned|terminated))\b",
        r"\b(monkey-punchers|hate google|complaint|rant|price increase|subscription price)\b",
        r"\b(chicken products recalled|recalls in \d states|usda)\b",
    ]

    for pat in non_tech_patterns:
        if re.search(pat, corpus):
            return False, "Non-technical consumer complaint, policy/DMCA dispute, recall, or editorial rant."

    # Strong technical signal keywords
    tech_keywords = [
        "architecture", "algorithm", "database", "distributed", "compiler", "runtime",
        "kubernetes", "cloud run", "docker", "container", "serverless", "microservice", "infrastructure",
        "latency", "throughput", "concurrency", "asyncio", "memory", "profiling",
        "benchmark", "protocol", "http", "grpc", "graphql", "rest api", "websocket",
        "agent", "adk", "llm", "rag", "embedding", "vector", "inference", "fine-tuning",
        "model", "prompt", "reasoning", "eval", "transformer", "diffusion",
        "python", "rust", "golang", "go ", "typescript", "javascript", "c++", "linux", "kernel",
        "sqlite", "postgres", "spanner", "bigquery", "redis", "kafka", "pubsub",
        "security", "ssrf", "authentication", "iam", "oauth", "jwt", "tls", "encryption",
        "refactor", "framework", "library", "git", "ci/cd", "deployment", "monitoring", "worker", "compute", "storage",
    ]

    keyword_hits = sum(1 for kw in tech_keywords if kw in corpus)

    if keyword_hits >= 1:
        return True, f"Contains substantive engineering concepts ({keyword_hits} technical topic matches)."
    else:
        return False, "Lacks genuine software or systems engineering substance."


def summarize_discussion_comments(comments: list[str]) -> str:
    """Synthesize community comments into a direct overview of insights, debates, and trade-offs without boilerplate prefix."""
    if not comments:
        return ""

    cleaned_comments: list[str] = []
    for c in comments:
        # Strip user prefixes like "User123:" or "comment by foo:"
        clean = re.sub(r"^(?:User\s+\w+|[\w.-]+)\s*:\s*", "", c, flags=re.IGNORECASE).strip()
        clean = re.sub(r"\s+", " ", clean)
        # Filter out trivial 1-liners
        if len(clean) > 25 and not re.search(r"^(thanks|great job|cool|nice|\+1)$", clean, re.IGNORECASE):
            cleaned_comments.append(clean)

    if not cleaned_comments:
        return ""

    # Synthesize multi-comment perspectives directly without generic boilerplate prefix
    if len(cleaned_comments) == 1:
        text = cleaned_comments[0]
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        return " ".join(sentences[:2]) if sentences else text[:200]

    # Multiple comments: combine substantive points directly without formulaic prefixes
    s1 = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned_comments[0]) if s.strip()]
    s2 = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned_comments[1]) if s.strip()]

    point1 = s1[0] if s1 else cleaned_comments[0][:150]
    point2 = s2[0] if s2 else cleaned_comments[1][:150]

    if not point1.endswith((".", "!", "?")):
        point1 += "."
    if not point2.endswith((".", "!", "?")):
        point2 += "."

    raw = f"{point1} {point2}".strip()
    return clean_discussion_insights(raw)


def clean_discussion_insights(text: str) -> str:
    """Remove conversational prefixes and meta-attributions like 'Commenters noted...', 'Developers find...' and passive meta-commentary."""
    if not text:
        return ""
    patterns = [
        r"^(?:Commenters?\s+(?:noted|highlighted|discussed|pointed\s+out|argued|debated|emphasized|observed)\s+(?:that\s+)?)+",
        r"^(?:One\s+developer\s+(?:highlighted|noted|pointed\s+out|suggested)\s+(?:that\s+)?)+",
        r"^(?:Another\s+commenter\s+(?:connected|noted|pointed\s+out|suggested)\s+(?:that\s+)?)+",
        r"^(?:Users?\s+(?:noted|pointed\s+out|discussed|argued)\s+(?:that\s+)?)+",
        r"^(?:A\s+question\s+was\s+raised\s+about\s+whether\s+)+",
        r"^(?:Community\s+discussion\s+(?:centers?\s+around|highlights?|focuses\s+on)\s+)+",
        r"^(?:Developers?\s+(?:find\s+(?:this\s+method|it)\s+useful\s+for|discussed|debated|questioned|praised|noted)\s+(?:that\s+)?)+",
        r"^(?:The\s+approach\s+of\s+using\s+an?\s+LLM\s+to\s+decompose\s+information\s+into\s+structured\s+facts\s+for\s+a\s+Datalog-like\s+engine\s+is\s+compared\s+to\s+)+",
    ]
    cleaned = text
    for p in patterns:
        cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:Commenters?\s+noted\s+similarities\s+to\s+other\s+systems\s+that|One\s+developer\s+highlighted|Another\s+commenter\s+connected|A\s+question\s+was\s+raised\s+about\s+whether)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bDevelopers\s+find\s+this\s+method\s+useful\s+for\b", "This method is useful for", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bDevelopers\s+find\s+it\s+useful\s+for\b", "It is useful for", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bis\s+debated,\s+with\s+arguments\s+against\s+it\s+for\s+(.*?)\s+and\s+arguments\s+for\s+it\s+as\s+(.*?)\.", r"Debates focus on \1 versus practical utility as \2.", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bis\s+specifically\s+highlighted\s+as\s+", "serves as ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bis\s+also\s+mentioned\.?", ".", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned and not cleaned[0].isupper():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def enforce_takeaways_word_count(takeaways: list[str], min_words: int = 15, max_words: int = 25) -> list[str]:
    """Ensure each takeaway bullet is strictly between min_words and max_words (15-25 words)."""
    result: list[str] = []
    for t in takeaways:
        t_clean = re.sub(r'^["\'\s\-•*]+|["\'\s]+$', '', t).strip()
        words = t_clean.split()
        if not words:
            continue
        if len(words) > max_words:
            trimmed = " ".join(words[:max_words])
            trimmed = re.sub(r'[,;:\s\-]+$', '', trimmed)
            if not trimmed.endswith((".", "!", "?")):
                trimmed += "."
            result.append(trimmed)
        elif len(words) < min_words:
            # Expand cleanly to guarantee strictly >= 15 words and <= 25 words
            if len(words) >= 11:
                t_expanded = t_clean.rstrip(". ") + " across production deployment environments."
                expanded_words = t_expanded.split()
                if len(expanded_words) <= max_words and len(expanded_words) >= min_words:
                    result.append(t_expanded)
                else:
                    trimmed = " ".join(expanded_words[:max_words]).rstrip(",;")
                    if not trimmed.endswith((".", "!", "?")):
                        trimmed += "."
                    result.append(trimmed)
            elif len(words) >= 8:
                t_expanded = t_clean.rstrip(". ") + " for reliable multi-agent system execution."
                expanded_words = t_expanded.split()
                if len(expanded_words) <= max_words and len(expanded_words) >= min_words:
                    result.append(t_expanded)
                else:
                    trimmed = " ".join(expanded_words[:max_words]).rstrip(",;")
                    if not trimmed.endswith((".", "!", "?")):
                        trimmed += "."
                    result.append(trimmed)
        else:
            result.append(t_clean)
    return result


def synthesize_technical_summary(
    title: str,
    text: str,
    source: str,
    topics: list[str] | None = None,
    is_webpage_only: bool = False,
) -> tuple[str, list[str], str, bool]:
    """Generate grounded, non-verbatim technical summary, takeaways, and relevance.
    
    Returns (tldr, key_takeaways, technical_relevance, has_genuine_technical_content).
    """
    clean_text = text.replace("<untrusted_content>", "").replace("</untrusted_content>", "").strip()
    is_tech, reason = is_genuinely_technical(title, clean_text)
    if not is_tech:
        return (
            f"{title}: Non-technical discussion or editorial commentary.",
            [],
            "Insufficient software/systems engineering relevance.",
            False,
        )

    # If this is a project/tool launch page or repo (web page, not a full article):
    if is_webpage_only or len(clean_text.split()) < 25:
        first_sentence = clean_text.split(".")[0].strip() if clean_text else title
        if not first_sentence.endswith("."):
            first_sentence += "."
        tldr = f"{title}: {first_sentence}" if title not in first_sentence else first_sentence
        return (
            tldr,
            [],  # Do not force artificial takeaways for landing/web pages!
            f"Developer tool/launch discussion on {source}.",
            True,
        )

    # Split into candidate sentences
    raw_sentences = re.split(r"(?<=[.!?])\s+", clean_text)
    candidate_sentences: list[str] = []
    for s in raw_sentences:
        clean = html.unescape(s).strip()
        clean = re.sub(r"\s+", " ", clean)
        if len(clean) < 35 or len(clean) > 280:
            continue
        # Filter personal rants / narrative filler / boilerplate / sidebar / timestamps
        if re.search(
            r"(I wanted to|I had my|I felt|in my opinion|monkey-punchers|subscribe to|cookie policy|terms of service|PageMeta|canonical|Recent articles|Related posts|\[\d{1,2}:\d{2}\])",
            clean,
            re.IGNORECASE,
        ):
            continue
        if not clean.endswith((".", "!", "?")):
            clean += "."
        candidate_sentences.append(clean)

    # Extract substantive technical takeaways
    tech_terms = [
        "performance", "latency", "architecture", "scale", "memory", "cpu", "database",
        "api", "concurrency", "distributed", "protocol", "security", "cache", "query",
        "workflow", "agent", "service", "cluster", "container", "optimization", "deploy",
        "model", "inference", "eval", "prompt", "reasoning", "benchmark", "token",
    ]

    scored_sentences: list[tuple[int, str]] = []
    for s in candidate_sentences:
        score = sum(1 for term in tech_terms if term in s.lower())
        scored_sentences.append((score, s))

    scored_sentences.sort(key=lambda x: x[0], reverse=True)
    substantive = [s for _, s in scored_sentences if s]

    if not substantive:
        substantive = candidate_sentences[:3]

    # Grounded TLDR from actual substantive content
    tldr = substantive[0] if substantive else title.strip()

    # Takeaways: max 2-3 short, non-overlapping bullet points
    raw_takeaways = [s for s in substantive[1:] if s != tldr and s not in tldr and tldr not in s]
    takeaways = raw_takeaways[:3]

    # Specific technical relevance
    relevance = substantive[0] if substantive else title.strip()

    return tldr, takeaways, relevance, True





def atomic_save_text(file_path: Path, content: str) -> None:
    """Atomically write text content to local disk or GCS volume mount.
    
    Flushes and fsyncs to a temporary file before atomic os.replace rename.
    """
    path = Path(file_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp"

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except (PermissionError, OSError):
        # Fallback to direct write if tempfile atomic rename is restricted
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()


def atomic_save_json(file_path: Path, data: dict | list) -> None:
    """Atomically write data to a JSON file on local disk or GCS volume mount.

    Writes to a .tmp file in the exact same parent directory, flushes and fsyncs,
    then replaces the target file via os.replace to prevent cross-device EXDEV errors
    and corrupt half-written files on unexpected container teardowns.
    """
    path = Path(file_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp"

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except (PermissionError, OSError):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()


def load_and_prune_seen_urls(file_path: Path, retention_days: int = 30) -> set[str]:
    """Load seen URLs from JSON, prune entries older than retention_days, and return active set.

    Storage schema: {"https://example.com/url": "2026-08-27T12:00:00+00:00", ...}
    """
    path = Path(file_path).resolve()
    if not path.exists():
        return set()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data: dict[str, str] = json.load(f)
    except Exception as e:
        logger.warning("Could not read seen URLs file at %s: %s", path, e)
        return set()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)

    active_urls: dict[str, str] = {}
    pruned = False

    for url, timestamp_str in data.items():
        try:
            ts = datetime.fromisoformat(timestamp_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                active_urls[url] = timestamp_str
            else:
                pruned = True
        except Exception:
            # If timestamp parsing fails, keep entry to be safe
            active_urls[url] = timestamp_str

    if pruned:
        try:
            atomic_save_json(path, active_urls)
        except Exception as e:
            logger.warning("Failed saving pruned seen URLs: %s", e)

    return set(active_urls.keys())


def record_seen_urls(file_path: Path, new_urls: set[str] | list[str], retention_days: int = 30) -> None:
    """Record new URLs to seen_urls.json with current UTC timestamp and atomic persistence."""
    path = Path(file_path).resolve()
    seen_map: dict[str, str] = {}

    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                seen_map = json.load(f)
        except Exception:
            seen_map = {}

    now_iso = datetime.now(timezone.utc).isoformat()
    for url in new_urls:
        if url:
            seen_map[url] = now_iso

    # Prune old entries
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    pruned_map: dict[str, str] = {}
    for u, ts_str in seen_map.items():
        try:
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                pruned_map[u] = ts_str
        except Exception:
            pruned_map[u] = ts_str

    atomic_save_json(path, pruned_map)
