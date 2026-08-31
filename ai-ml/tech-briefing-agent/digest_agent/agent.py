"""ADK 2.0 Workflow definition for Personal Tech-Briefing Digest Agent.

Builds the graph workflow consisting of:
- fetch_feeds: Ingests candidate articles and filters seen URLs.
- filter_articles: Selects top articles matching user interests and memory guidance using Gemini.
- extract_content: Safely extracts webpage text and comments, pruning inaccessible articles.
- summarize_article: Concurrently summarizes articles and community discussions with Gemini.
- verify_and_reflect_quality: Evaluates technical grounding, filters non-technical news, updates memory, and loops back to filter_articles if quota (< 2 articles) is not met.
- compile_briefing: Formats daily markdown digest briefing with Technical Takeaways & Community Insights.
- verify_editorial_coherence: Audits editorial narrative and developer relevance.
- save_digest: Persists markdown to /data/digests and updates seen_urls.json state.
"""

import asyncio
from datetime import datetime, timezone
import html
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from digest_agent.config import (
    DEFAULT_FEEDS,
    DEFAULT_INTERESTS,
    DEFAULT_MODEL,
    DIGESTS_DIR,
    MAX_CONCURRENCY,
    RETENTION_DAYS,
    SEEN_URLS_FILE,
)
from digest_agent.schemas import (
    ArticleMetadata,
    ArticleSummary,
    DailyDigest,
    EditorialSynthesis,
    EditorialVerificationResult,
    FilteredArticleList,
    QualityBatchEvaluation,
    QualityEvaluationItem,
    SessionShortTermMemory,
    UserInterests,
)
from digest_agent.utils import (
    atomic_save_json,
    atomic_save_text,
    canonicalize_url,
    clean_discussion_insights,
    compute_deterministic_relevance_score,
    enforce_takeaways_word_count,
    fetch_hn_top_comments,
    fetch_hn_top_stories,
    fetch_rss_feeds,
    is_genuinely_technical,
    is_substantive_content,
    load_and_prune_seen_urls,
    record_seen_urls,
    safe_extract_webpage,
    summarize_discussion_comments,
    synthesize_technical_summary,
    verify_link_liveliness,
    wrap_untrusted_discussion,
)

logger = logging.getLogger(__name__)

MAX_EDITORIAL_RETRIES: int = 2

# Try importing ADK 2.0 primitives, or define standard ADK 2.0 compatible classes
try:
    from google.adk import Workflow, LlmAgent, node, START, END  # type: ignore
except ImportError:
    START = "__START__"
    END = "__END__"

    def node(parallel_worker: bool = False) -> Callable:
        """Decorator to designate an ADK 2.0 workflow node."""
        def decorator(func: Callable) -> Callable:
            setattr(func, "__is_adk_node__", True)
            setattr(func, "__parallel_worker__", parallel_worker)
            return func
        return decorator

    class LlmAgent:
        """ADK 2.0 LlmAgent abstraction for structured generation."""
        def __init__(
            self,
            name: str,
            model: str = DEFAULT_MODEL,
            system_instruction: str = "",
            output_schema: Any = None,
        ) -> None:
            self.name = name
            self.model = model
            self.system_instruction = system_instruction
            self.output_schema = output_schema

    class Workflow:
        """ADK 2.0 Workflow graph orchestrator."""
        def __init__(self, name: str, edges: list[tuple[Any, Any]] | None = None) -> None:
            self.name = name
            self.edges = edges or []
            self._nodes: dict[str, Callable] = {}

        def add_node(self, name: str, func: Callable) -> None:
            self._nodes[name] = func

        def add_edge(self, source: Any, target: Any) -> None:
            self.edges.append((source, target))


def _get_genai_client() -> Any:
    """Initialize google-genai client with API key, Vertex AI, or ADC."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    try:
        from google import genai
        if api_key:
            return genai.Client(api_key=api_key)
        
        project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID") or os.getenv("GCP_PROJECT") or "shir-training"
        location = os.getenv("GOOGLE_CLOUD_REGION") or os.getenv("LOCATION", "us-west1")
        if project:
            return genai.Client(vertexai=True, project=project, location=location)
        
        return genai.Client()
    except Exception as e:
        logger.debug("Google GenAI client not initialized: %s", e)
        return None


# =====================================================================
# Workflow Node Implementations
# =====================================================================

@node()
async def fetch_feeds_node(state: dict[str, Any]) -> dict[str, Any]:
    """Fetch candidate articles from Hacker News and RSS feeds, filtering out seen URLs and enforcing 14-day freshness with DRS scoring."""
    feeds = state.get("feeds", DEFAULT_FEEDS)
    force_refresh = state.get("force_refresh", False)

    # Ingest HN and RSS in parallel with 14-day freshness window
    hn_task = fetch_hn_top_stories(limit=35, min_score=20, max_days=14)
    rss_task = fetch_rss_feeds(feeds, max_days=14)
    hn_articles, rss_articles = await asyncio.gather(hn_task, rss_task)

    all_articles = hn_articles + rss_articles

    # Filter seen URLs using canonicalized representations
    seen_raw = set() if force_refresh else load_and_prune_seen_urls(SEEN_URLS_FILE, RETENTION_DAYS)
    seen_urls = {canonicalize_url(u) for u in seen_raw}

    candidates: list[ArticleMetadata] = []
    seen_in_batch: set[str] = set()

    for art in all_articles:
        canon_url = canonicalize_url(art.url)
        if not canon_url or canon_url in seen_urls or canon_url in seen_in_batch:
            continue

        # Evaluate deterministic relevance score (DRS) and technical validity
        drs_score, is_acceptable, reason = compute_deterministic_relevance_score(
            title=art.title,
            snippet=art.snippet,
            source=art.source,
            url=canon_url,
            score=art.score,
            comments_count=art.comments_count,
        )

        if not is_acceptable:
            logger.debug("Ingestion skipped candidate '%s': %s", art.title, reason)
            continue

        art.url = canon_url
        art.importance_score = drs_score
        candidates.append(art)
        seen_in_batch.add(canon_url)

    # Strict multi-key sort guaranteeing 100% deterministic candidate ordering across runs
    candidates.sort(key=lambda x: (-x.importance_score, -x.score, -x.comments_count, canonicalize_url(x.url)))

    logger.info("Fetched %d raw articles, %d fresh high-signal candidates after DRS evaluation & deduplication", len(all_articles), len(candidates))
    state["candidate_articles"] = candidates
    if "session_memory" not in state:
        state["session_memory"] = SessionShortTermMemory()
    return state


@node()
async def filter_articles_node(state: dict[str, Any]) -> dict[str, Any]:
    """Select candidate articles matching user interests and high engagement, guided by short-term memory."""
    candidates: list[ArticleMetadata] = state.get("candidate_articles", [])
    memory: SessionShortTermMemory = state.get("session_memory", SessionShortTermMemory())
    interests: UserInterests = state.get(
        "user_interests",
        UserInterests(topics=DEFAULT_INTERESTS, max_articles=5)
    )

    approved_count = len(memory.approved_summaries)
    target_cap = min(5, interests.max_articles)
    needed_count = target_cap - approved_count

    if needed_count <= 0:
        logger.info("Memory already has %d approved articles (quota %d met). Skipping filter.", approved_count, target_cap)
        state["filtered_articles"] = FilteredArticleList(selected_articles=[], reasoning="Quota already satisfied.")
        return state

    # Exclude already seen, approved, or explicitly rejected URLs from previous passes (canonicalized)
    excluded_urls = {canonicalize_url(u) for u in memory.rejected_urls} | {canonicalize_url(s.url) for s in memory.approved_summaries}
    available_candidates = [c for c in candidates if canonicalize_url(c.url) not in excluded_urls]

    if not available_candidates:
        logger.info("No more unexamined candidates available.")
        state["filtered_articles"] = FilteredArticleList(selected_articles=[], reasoning="Candidate pool exhausted.")
        return state

    # Ensure stable sorting before prompt formatting
    available_candidates.sort(key=lambda x: (-x.importance_score, -x.score, -x.comments_count, canonicalize_url(x.url)))

    client = _get_genai_client()
    model_name = state.get("model", DEFAULT_MODEL)

    if client:
        try:
            from google.genai import types
            guidance_prompt = ""
            if memory.filter_guidance:
                guidance_prompt = f"\nFEEDBACK & GUIDANCE FROM PREVIOUS REFLECTION PASSES:\n" + "\n".join(f"- {g}" for g in memory.filter_guidance) + "\n"

            prompt = (
                f"User Technical Interests: {json.dumps(interests.topics)}\n"
                f"Articles Needed in This Pass: {needed_count} (Maximum Total: {target_cap})\n"
                f"Minimum Score Threshold: {interests.min_score}\n"
                f"{guidance_prompt}\n"
                f"Candidate Articles (Ranked deterministically by AI/Systems Relevance Score):\n"
            )
            for idx, c in enumerate(available_candidates[:30], 1):
                prompt += (
                    f"{idx}. [{c.source}] {c.title} (URL: {c.url})\n"
                    f"   Relevance Score: {c.importance_score:.1f} | Points: {c.score} | Comments: {c.comments_count}\n"
                    f"   Snippet: {c.snippet}\n"
                )

            sys_instruction = (
                "You are the Principal AI & Systems Architect curating a specialized developer technical briefing.\n"
                "STRICT SELECTION CRITERIA:\n"
                "1. Select ONLY substantive articles with broad software engineering, cloud systems architecture, or high-impact AI/ML developer relevance.\n"
                "2. STRICTLY REJECT overly niche/obscure micro-topics, hyper-narrow domain tools, minor library release notes (e.g., plugin version bumps like 'llm-anthropic 0.27' or minor bugfixes), changelogs, quote stubs, non-architectural database/file format trivia, consumer app complaints, DMCA notices, copyright drama, app store disputes, or superficial business PR.\n"
                "3. PRIORITIZE: AI agents, workflow graphs, model serving, prompt design, reasoning systems, LLM evaluation, systems programming, and cloud infrastructure.\n"
                "4. MANDATORY HACKER NEWS REQUIREMENT: You MUST ALWAYS include at least 1 top technical item from Hacker News (Show HNs, architectural debates, LLM benchmarks) among your selected articles.\n"
                "5. ENFORCE CHANNEL & SOURCE DIVERSITY: Ensure a balanced representation of the ecosystem. Select at least 1-3 top technical community discussions from Hacker News and at most 1 article per specific engineering blog (e.g. maximum 1 from LangChain, maximum 1 from Latent Space, maximum 1 from Lil'Log/Simon Willison). NEVER select multiple articles from the same engineering blog.\n"
                "6. Select up to the requested number of articles. If only 2-3 high-quality articles exist, select only those—do not force-fill with low-signal articles.\n"
                "7. Be completely deterministic in your evaluation.\n"
                "Return strict JSON matching the FilteredArticleList schema."
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    response_mime_type="application/json",
                    response_schema=FilteredArticleList,
                    temperature=0.0,
                    seed=42,
                ),
            )
            filtered = FilteredArticleList.model_validate_json(response.text)
            
            # Re-hydrate articles with full candidate metadata (discussion_url, points, comments)
            candidate_by_url = {canonicalize_url(c.url): c for c in available_candidates}
            candidate_by_title = {c.title.strip().lower(): c for c in available_candidates}
            rehydrated: list[ArticleMetadata] = []
            for a in filtered.selected_articles:
                canon = canonicalize_url(a.url)
                matched = candidate_by_url.get(canon) or candidate_by_title.get(a.title.strip().lower())
                if matched:
                    a.url = matched.url
                    a.title = matched.title
                    a.discussion_url = matched.discussion_url
                    a.score = matched.score
                    a.comments_count = matched.comments_count
                    a.published_at = matched.published_at if matched.published_at and matched.published_at.lower() not in ("unknown", "", "none") else (a.published_at or "Recent")
                    a.source = matched.source if matched.source and matched.source not in ("Unknown", "") else a.source
                    a.read_time = matched.read_time if matched.read_time and matched.read_time.lower() not in ("unknown", "", "none") else (a.read_time or "3 min read")
                    a.comments_text = matched.comments_text
                rehydrated.append(a)

            # Programmatically enforce diversity cap: max 1 per blog source, max 2 for Hacker News (never > 2 from any source)
            diverse_articles: list[ArticleMetadata] = []
            source_seen_counts: dict[str, int] = {}
            for a in rehydrated:
                is_hn = "hacker news" in a.source.lower()
                limit_for_src = 2 if is_hn else 1
                curr_count = source_seen_counts.get(a.source.lower(), 0)
                if curr_count < limit_for_src:
                    diverse_articles.append(a)
                    source_seen_counts[a.source.lower()] = curr_count + 1

            # MANDATORY GUARANTEE: Ensure at least 1 Hacker News item is included from the last 2 weeks
            has_hn = any("hacker news" in a.source.lower() for a in diverse_articles)
            if not has_hn:
                top_hn = next((c for c in available_candidates if "hacker news" in c.source.lower() and not any(canonicalize_url(c.url) == canonicalize_url(da.url) for da in diverse_articles)), None)
                if top_hn:
                    if len(diverse_articles) >= needed_count and diverse_articles:
                        # Replace the lowest scoring item with the top HN candidate
                        diverse_articles[-1] = top_hn
                    else:
                        diverse_articles.append(top_hn)

            # If we need more to reach needed_count, backfill from available candidates adhering to source caps (max 1-2)
            if len(diverse_articles) < needed_count:
                for cand in available_candidates:
                    if len(diverse_articles) >= needed_count:
                        break
                    if any(canonicalize_url(cand.url) == canonicalize_url(da.url) for da in diverse_articles):
                        continue
                    is_hn = "hacker news" in cand.source.lower()
                    limit_for_src = 2 if is_hn else 1
                    curr_count = source_seen_counts.get(cand.source.lower(), 0)
                    if curr_count < limit_for_src:
                        diverse_articles.append(cand)
                        source_seen_counts[cand.source.lower()] = curr_count + 1

            filtered.selected_articles = diverse_articles[:needed_count]
            state["filtered_articles"] = filtered
            return state
        except Exception as e:
            logger.warning("LLM article filtering failed, falling back to deterministic heuristic scoring: %s", e)

    # Deterministic fallback selection based on DRS ranking + source diversity cap (max 1 per blog, max 2 for HN)
    selected: list[ArticleMetadata] = []
    source_counts: dict[str, int] = {}
    
    # First pass: Mandatory Hacker News selection (at least 1, up to 2)
    for cand in available_candidates:
        if len(selected) >= min(2, needed_count):
            break
        if "hacker news" in cand.source.lower():
            s_key = cand.source.lower()
            s_count = source_counts.get(s_key, 0)
            if s_count < 2:
                selected.append(cand)
                source_counts[s_key] = s_count + 1

    # Second pass: High-relevance engineering blogs (max 1 per blog domain)
    for cand in available_candidates:
        if len(selected) >= needed_count:
            break
        if any(canonicalize_url(cand.url) == canonicalize_url(s.url) for s in selected):
            continue
        s_key = cand.source.lower()
        s_count = source_counts.get(s_key, 0)
        is_hn = "hacker news" in s_key
        limit_for_src = 2 if is_hn else 1
        if s_count < limit_for_src:
            selected.append(cand)
            source_counts[s_key] = s_count + 1

    state["filtered_articles"] = FilteredArticleList(
        selected_articles=selected,
        reasoning="Selected based on deterministic relevance score (DRS), mandatory Hacker News inclusion, and non-niche systems relevance."
    )
    return state


@node()
async def extract_content_node(state: dict[str, Any]) -> dict[str, Any]:
    """Safely extract webpage text and discussion comments, pruning inaccessible or non-substantive articles."""
    filtered: FilteredArticleList = state.get("filtered_articles", FilteredArticleList())
    articles = filtered.selected_articles
    memory: SessionShortTermMemory = state.get("session_memory", SessionShortTermMemory())
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def _extract(art: ArticleMetadata) -> tuple[ArticleMetadata, str] | None:
        async with semaphore:
            # 1. Concurrently extract webpage content and fetch discussion comments
            extract_task = safe_extract_webpage(art.url)
            
            # Extract story id if Hacker News discussion link
            fetch_comments = False
            story_id = 0
            if art.discussion_url and "news.ycombinator.com/item?id=" in art.discussion_url:
                try:
                    parsed = urlparse(art.discussion_url)
                    qs = parse_qs(parsed.query)
                    story_id_str = qs.get("id", [""])[0]
                    if story_id_str.isdigit():
                        story_id = int(story_id_str)
                        fetch_comments = True
                except Exception:
                    pass

            if fetch_comments:
                content, comments = await asyncio.gather(extract_task, fetch_hn_top_comments(story_id, max_comments=5))
            else:
                content = await extract_task
                comments = []

            art.comments_text = comments or []

            # Check if this is a web page / project landing page or full article
            clean_body = content.replace("<untrusted_content>", "").replace("</untrusted_content>", "").strip()
            word_count = len(clean_body.split())

            if word_count < 50:
                if len(art.comments_text) > 0:
                    # It's a launch/project landing page with rich community discussion!
                    art.is_webpage_only = True
                    art.has_full_article_content = False
                    art.is_verified = True
                    return art, content
                else:
                    # Inaccessible or empty page with no comments
                    logger.warning("Pruning inaccessible/low-substance article (<50 words, no comments): %s (%s)", art.title, art.url)
                    memory.rejected_urls.append(art.url)
                    memory.rejected_articles.append({
                        "url": art.url,
                        "title": art.title,
                        "reason": "Inaccessible article content (< 50 substantive words; paywalled, blocked, or 404).",
                        "phase": "extraction"
                    })
                    memory.filter_guidance.append(f"Do not select {art.url} ({art.title}) as webpage content is inaccessible.")
                    return None
            elif word_count < 150:
                art.is_webpage_only = True
                art.has_full_article_content = True
                art.is_verified = True
                return art, content
            else:
                art.is_webpage_only = False
                art.has_full_article_content = True
                art.is_verified = True
                return art, content

    results = await asyncio.gather(*[_extract(art) for art in articles])
    extracted_valid = [r for r in results if r is not None]
    state["extracted_articles"] = extracted_valid
    state["session_memory"] = memory
    return state


@node(parallel_worker=True)
async def summarize_article_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate structured summaries and discussion insights for extracted articles using Gemini or grounded technical synthesis."""
    extracted_articles: list[tuple[ArticleMetadata, str]] = state.get("extracted_articles", [])
    memory: SessionShortTermMemory = state.get("session_memory", SessionShortTermMemory())
    client = _get_genai_client()
    model_name = state.get("model", DEFAULT_MODEL)
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def _summarize_single(art: ArticleMetadata, raw_content: str) -> ArticleSummary:
        async with semaphore:
            is_webpage = getattr(art, "is_webpage_only", False)
            clean_text = raw_content.replace("<untrusted_content>", "").replace("</untrusted_content>", "").strip()
            critiques = "\n".join(f"- {c}" for c in memory.summarization_critique) if memory.summarization_critique else ""
            
            wrapped_discussion = ""
            if art.comments_text:
                joined_comments = "\n---\n".join(art.comments_text[:5])
                wrapped_discussion = f"<community_discussion>\n{joined_comments}\n</community_discussion>"

            if client:
                try:
                    from google.genai import types
                    sys_instruction = (
                        "You are an AI/ML Principal Systems Architect reviewing technical engineering articles and developer discussions for senior software engineers.\n"
                        "CRITICAL ARCHITECTURAL CONSTRAINTS:\n"
                        "1. Scope Separation between TL;DR and Key Takeaways:\n"
                        "   - tldr: Exclusively state the *what* and *why* (the high-level product/project pitch and core problem solved in 1-2 concise sentences). Do NOT mention specific implementation details, specific database names, parameters, or low-level mechanisms in the TL;DR.\n"
                        "   - key_takeaways: Exclusively state the *how* (concrete architectural mechanisms, internal engine design, state checkpointing, specific APIs/parameters, benchmarks, or trade-offs). Provide exactly 2-3 bullet points. Each bullet point MUST be strictly between 17 and 23 words in length (NEVER fewer than 15 words and NEVER more than 25 words). Crucially: Takeaways MUST have ZERO conceptual or lexical overlap with the TL;DR. Every bullet must provide new technical depth not mentioned in the TL;DR. Do not include quotes or conversational framing.\n"
                        "2. Webpage/Launch vs Full Article:\n"
                        "   - If the URL is a project repository or short landing page: set is_webpage_only=True, tldr to 1 crisp sentence, and key_takeaways to [].\n"
                        "   - If the URL is a full technical article: set is_webpage_only=False, and provide 2-3 distinct technical takeaways.\n"
                        "3. Community Discussion Synthesis:\n"
                        "   - If <community_discussion> is present: Synthesize community sentiment and technical trade-offs as direct, active factual assertions. NEVER use meta-commentary, passive framing, human attributions, or conversational prefixes (BANNED: 'Commenters noted', 'Developers find', 'One developer highlighted', 'is debated', 'is mentioned', 'is highlighted', 'A question was raised', 'Discussion centers'). State the technical arguments directly as objective factual claims (e.g. 'Anthropomorphizing AI systems distorts mechanical understanding; however, modeling open-ended search states as unstructured exploration provides a useful conceptual parallel for evaluating agent autonomy.').\n"
                        "   - If NO community discussion is provided: You MUST set discussion_summary to an empty string \"\".\n"
                        "4. Grounding: Set has_genuine_technical_content=False if the article lacks systems/software engineering substance."
                    )

                    critique_prompt = f"\nSUMMARIZATION CRITIQUE FROM MEMORY:\n{critiques}\n" if critiques else ""

                    prompt = (
                        f"Article Title: {art.title}\n"
                        f"Source: {art.source}\n"
                        f"URL: {art.url}\n"
                        f"Discussion URL: {art.discussion_url or 'N/A'}\n"
                        f"Engagement: {art.score} points, {art.comments_count} comments\n"
                        f"Published Date: {art.published_at or 'Recent'}\n"
                        f"Estimated Read Time: {art.read_time or '3 min read'}\n"
                        f"Is Webpage/Launch Only: {art.is_webpage_only}\n"
                        f"{critique_prompt}\n"
                        f"<article_content>\n{clean_text}\n</article_content>\n"
                        f"{wrapped_discussion}\n"
                    )

                    def _call_gemini() -> Any:
                        return client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=sys_instruction,
                                response_mime_type="application/json",
                                response_schema=ArticleSummary,
                                temperature=0.0,
                                seed=42,
                            ),
                        )

                    response = await asyncio.to_thread(_call_gemini)
                    summary = ArticleSummary.model_validate_json(response.text)

                    # Ensure takeaways are bounded to max 3 items, clean from quotes, non-overlapping with tldr, and strictly 15-25 words
                    if summary.key_takeaways:
                        cleaned_kw = []
                        for t in summary.key_takeaways:
                            t_clean = re.sub(r'^["\'\s\-•*]+|["\'\s]+$', '', t).strip()
                            if t_clean and t_clean != summary.tldr and t_clean not in summary.tldr:
                                cleaned_kw.append(t_clean)
                        summary.key_takeaways = enforce_takeaways_word_count(cleaned_kw[:3], min_words=15, max_words=25)

                    summary.url = art.url
                    summary.title = art.title
                    summary.source = art.source
                    summary.discussion_url = art.discussion_url
                    summary.score = art.score
                    summary.comments_count = art.comments_count
                    if not summary.discussion_summary and art.comments_text:
                        summary.discussion_summary = summarize_discussion_comments(art.comments_text)
                    if summary.discussion_summary:
                        summary.discussion_summary = clean_discussion_insights(summary.discussion_summary)
                    if not summary.read_time or summary.read_time.lower() in ("unknown", "", "none"):
                        summary.read_time = art.read_time if (art.read_time and art.read_time.lower() not in ("unknown", "", "none")) else "3 min read"
                    if not summary.published_at or summary.published_at.lower() in ("unknown", "", "none"):
                        summary.published_at = art.published_at if (art.published_at and art.published_at.lower() not in ("unknown", "", "none")) else "Recent"
                    
                    return summary
                except Exception as e:
                    logger.warning("Gemini summarization failed for '%s', falling back to deterministic synthesis: %s", art.title, e)

            # Deterministic fallback synthesis
            tldr, takeaways, relevance, is_tech = synthesize_technical_summary(
                title=art.title,
                text=raw_content,
                source=art.source,
                is_webpage_only=is_webpage,
            )
            disc_summary = summarize_discussion_comments(art.comments_text) if art.comments_text else ""

            return ArticleSummary(
                title=art.title,
                url=art.url,
                source=art.source,
                discussion_url=art.discussion_url,
                read_time=art.read_time or "3 min read",
                published_at=art.published_at,
                score=art.score,
                comments_count=art.comments_count,
                is_verified=art.is_verified,
                quality_score=8 if is_tech else 3,
                quality_rationale="Grounded technical synthesis with discussion analysis." if is_tech else "Lacks technical depth.",
                tldr=tldr,
                key_takeaways=[] if is_webpage else takeaways[:3],
                discussion_summary=disc_summary,
                technical_relevance=relevance,
                has_genuine_technical_content=is_tech,
                is_grounded_in_article=True,
                is_webpage_only=is_webpage,
            )

    try:
        summaries = await asyncio.gather(*[_summarize_single(art, content) for art, content in extracted_articles])
        state["candidate_summaries"] = summaries
        state["summaries"] = summaries
        return state
    except Exception as e:
        logger.error("summarize_article_node error: %s", e)
        state["candidate_summaries"] = []
        state["summaries"] = []
        return state


@node()
async def verify_and_reflect_quality_node(state: dict[str, Any]) -> dict[str, Any]:
    """Reflect on summary quality, verify links, evaluate hallucinations, and optimize editorial precision."""
    candidate_summaries: list[ArticleSummary] = state.get("candidate_summaries") or state.get("summaries", [])
    memory: SessionShortTermMemory = state.get("session_memory", SessionShortTermMemory())
    loop1_iteration: int = state.get("loop1_iteration", 0)

    # 1. Verify link liveliness for candidate summaries
    async def _verify_article_links(s: ArticleSummary) -> None:
        is_known_community = bool(s.discussion_url and ("news.ycombinator.com/item" in s.discussion_url or "reddit.com/r/" in s.discussion_url))
        is_canonical_alive = await verify_link_liveliness(s.url)
        is_discussion_alive = True if is_known_community else (await verify_link_liveliness(s.discussion_url) if s.discussion_url else False)

        if not is_discussion_alive and s.discussion_url != s.url and not is_known_community:
            s.discussion_url = None

        if not is_canonical_alive:
            # If canonical link check had transient failure but discussion is alive, keep both
            s.is_verified = bool(is_discussion_alive or is_known_community)
        else:
            s.is_verified = True

    await asyncio.gather(*[_verify_article_links(s) for s in candidate_summaries])

    # 2. LLM or Heuristic Quality Reflection Judge
    client = _get_genai_client()
    model_name = state.get("model", DEFAULT_MODEL)

    if client and candidate_summaries:
        try:
            from google.genai import types
            prompt = "Audit the following candidate summaries for technical depth, grounding, developer relevance, and discussion insights:\n\n"
            for idx, s in enumerate(candidate_summaries, 1):
                prompt += (
                    f"Article {idx}:\n"
                    f"- Title: {s.title}\n"
                    f"- URL: {s.url}\n"
                    f"- Source: {s.source}\n"
                    f"- TL;DR: {s.tldr}\n"
                    f"- Key Takeaways: {json.dumps(s.key_takeaways)}\n"
                    f"- Discussion Summary: {s.discussion_summary}\n"
                    f"- Technical Relevance: {s.technical_relevance}\n"
                    f"- Has Genuine Technical Content: {s.has_genuine_technical_content}\n\n"
                )

            sys_instruction = (
                "You are an AI Quality & Reflection Judge for senior software engineers.\n"
                "Evaluate each summary:\n"
                "1. If the article is not genuinely about software/systems engineering or developer architecture (e.g. DMCA notice, app store policy drama, non-technical hype), set should_drop=True and is_technically_relevant=False.\n"
                "2. If the summary is well-grounded with actionable engineering takeaways, set should_drop=False and quality_score >= 7.\n"
                "Return strict JSON matching QualityBatchEvaluation."
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    response_mime_type="application/json",
                    response_schema=QualityBatchEvaluation,
                    temperature=0.0,
                    seed=42,
                ),
            )
            eval_batch = QualityBatchEvaluation.model_validate_json(response.text)
            eval_map = {e.url: e for e in eval_batch.evaluations}
            for s in candidate_summaries:
                if s.url in eval_map:
                    ev = eval_map[s.url]
                    s.quality_score = ev.quality_score
                    s.quality_rationale = ev.quality_rationale
                    s.is_grounded_in_article = ev.is_grounded
                    s.has_genuine_technical_content = ev.is_technically_relevant
                    if ev.should_drop or not ev.is_technically_relevant or ev.quality_score < 6:
                        s.has_genuine_technical_content = False

        except Exception as e:
            logger.warning("Quality reflection batch pass failed: %s", e)

    # 3. Categorize candidates into Approved vs Rejected in Short-Term Memory
    for s in candidate_summaries:
        if not s.is_verified or not s.has_genuine_technical_content or not s.is_grounded_in_article or s.quality_score < 6:
            # Reject and record feedback to memory
            if s.url not in memory.rejected_urls:
                memory.rejected_urls.append(s.url)
                reason = s.quality_rationale or "Lacks genuine software/systems engineering substance or failed verification."
                memory.rejected_articles.append({
                    "url": s.url,
                    "title": s.title,
                    "reason": reason,
                    "phase": "verification"
                })
                memory.filter_guidance.append(f"Exclude articles similar to '{s.title}': {reason}")
                logger.info("Rejected low-substance/non-technical article: %s (%s)", s.title, reason)
        else:
            # Approved! Add to approved list if not already present
            if not any(a.url == s.url for a in memory.approved_summaries):
                memory.approved_summaries.append(s)
                logger.info("Approved high-quality technical summary: %s (Quality Score: %d/10)", s.title, s.quality_score)

    total_approved = len(memory.approved_summaries)
    logger.info("Loop 1 reflection state: %d approved articles in memory (iteration %d)", total_approved, loop1_iteration)

    # 4. Check Termination Condition
    if "loop1_iteration" not in state:
        state["summaries"] = memory.approved_summaries
        state["loop1_continue"] = False
    elif total_approved >= 2 or loop1_iteration >= 1:
        state["loop1_continue"] = False
        state["summaries"] = memory.approved_summaries[:5]
        logger.info("Loop 1 complete with %d approved articles. Proceeding to compilation.", len(state["summaries"]))
    else:
        # Not enough approved articles and retries remaining: loop back to filter_articles
        state["loop1_iteration"] = loop1_iteration + 1
        state["loop1_continue"] = True
        logger.info("Loop 1 active: Quota not yet met (%d/2 minimum). Routing back to filter_articles with memory guidance.", total_approved)

    state["session_memory"] = memory
    return state


@node()
async def compile_briefing_node(state: dict[str, Any]) -> dict[str, Any]:
    """Assemble individual summaries into a publication-ready Markdown digest document with Technical Takeaways & Community Insights."""
    summaries: list[ArticleSummary] = state.get("summaries", [])
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_human = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
    client = _get_genai_client()
    model_name = state.get("model", DEFAULT_MODEL)

    # Deterministic Markdown Assembly
    md_lines = [
        f"# Personal Tech-Briefing Digest",
        f"**Date:** {now_human}  ",
        f"**Target Infrastructure:** Google Cloud Run Instances | ADK 2.0  ",
        f"**Articles Curated:** {len(summaries)}  ",
        "",
        "---",
        "",
        "### Table of Contents",
    ]

    for idx, s in enumerate(summaries, 1):
        if s.score > 0 and s.comments_count > 0:
            score_badge = f" [🔥 {s.score} pts • 💬 {s.comments_count}]"
        elif s.score > 0:
            score_badge = f" [🔥 {s.score} pts]"
        else:
            score_badge = " [📰 Curated]"
        md_lines.append(f"{idx}. [{s.title}](#article-{idx}) — *{s.source}*{score_badge} ({s.read_time})")

    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

    for idx, s in enumerate(summaries, 1):
        # Format links clearly: direct article link + Hacker News/community discussion link
        if s.source == "Hacker News" or (s.discussion_url and "news.ycombinator.com" in s.discussion_url):
            c_label = f"💬 Hacker News Discussion ({s.comments_count} comments)" if s.comments_count > 0 else "💬 Hacker News Discussion"
            if s.discussion_url and s.url != s.discussion_url:
                links_line = f"[🔗 Read Article / Webpage]({s.url}) • [{c_label}]({s.discussion_url})"
            elif s.discussion_url:
                links_line = f"[🔗 Read Article / Webpage]({s.discussion_url}) • [{c_label}]({s.discussion_url})"
            else:
                links_line = f"[🔗 Read Article / Webpage]({s.url})"
        elif s.discussion_url and s.discussion_url != s.url and not any(s.discussion_url.endswith(ext) or ext in s.discussion_url for ext in (".xml", ".rss", "/feed", "/atom", "atom.xml", "rss.xml")):
            if "reddit.com" in s.discussion_url:
                c_label = f"💬 Reddit Discussion ({s.comments_count} comments)" if s.comments_count > 0 else "💬 Reddit Discussion"
                links_line = f"[🔗 Read Article / Webpage]({s.url}) • [{c_label}]({s.discussion_url})"
            else:
                c_label = f"💬 Discussion Thread ({s.comments_count} comments)" if s.comments_count > 0 else "💬 Discussion Thread"
                links_line = f"[🔗 Read Article / Webpage]({s.url}) • [{c_label}]({s.discussion_url})"
        else:
            links_line = f"[🔗 Read Article / Webpage]({s.url})"

        # Engagement badge formatting
        if s.score > 0 and s.comments_count > 0:
            engagement_badge = f" • **Engagement:** 🔥 {s.score} pts • 💬 {s.comments_count} comments"
        elif s.score > 0:
            engagement_badge = f" • **Engagement:** 🔥 {s.score} pts"
        else:
            engagement_badge = " • **Type:** 📰 Curated Engineering Post"

        pub_info = f" • **Published:** {s.published_at}" if s.published_at else ""
        verified_badge = " • 🛡️ *Verified Source*" if s.is_verified else ""
        
        tldr_label = "Project/Tool Overview" if s.is_webpage_only or not s.key_takeaways else "TL;DR"
        md_lines.extend([
            f"<a id=\"article-{idx}\"></a>",
            f"## {idx}. [{s.title}]({s.url})",
            f"**Source:** {s.source} • **Read time:** {s.read_time}{engagement_badge}{pub_info}{verified_badge}",
            "",
            f"**Links:** {links_line}",
            "",
            f"> **{tldr_label}:** {s.tldr}",
            "",
        ])

        if not s.is_webpage_only and s.key_takeaways:
            md_lines.append("#### Main Takeaways for Developers")
            for bullet in s.key_takeaways:
                md_lines.append(f"- {bullet}")
            md_lines.append("")

        if s.discussion_summary:
            clean_disc = re.sub(
                r"^(?:Community\s+discussion\s+(?:highlights|indicates|reveals|shows)[^:]*:\s*|Community\s+discussion:\s*|Commenters\s+discuss[^:]*:\s*)",
                "",
                s.discussion_summary,
                flags=re.IGNORECASE,
            ).strip()
            # Strip any leading blockquote markers from discussion comments so they render as prose/bullets
            clean_disc_lines = [re.sub(r"^\s*>\s*", "", line) for line in clean_disc.split("\n")]
            clean_disc = "\n".join(clean_disc_lines).strip()
            if clean_disc:
                md_lines.extend([
                    "#### Developer Insights from Comments",
                    clean_disc,
                    "",
                ])

        md_lines.extend([
            "---",
            "",
        ])

    md_lines.extend([
        "## System Status & Metadata",
        f"- **Generated At:** `{datetime.now(timezone.utc).isoformat()}`",
        f"- **Engine:** Google Agent Development Kit 2.0 (Workflow API with Memory-Guided Adaptive Reflection)",
        f"- **Compute Primitive:** Google Cloud Run Instances (Singleton)",
        "",
    ])

    markdown_content = "\n".join(md_lines)

    digest = DailyDigest(
        title=f"Personal Tech Briefing - {today_str}",
        date=today_str,
        executive_synthesis="",
        summaries=summaries,
        markdown_content=markdown_content,
    )

    state["daily_digest"] = digest
    return state


@node()
async def verify_editorial_coherence_node(state: dict[str, Any]) -> dict[str, Any]:
    """Verify that the compiled briefing makes sense as a cohesive whole, checking developer relevance and managing Loop 2 retries."""
    digest: DailyDigest = state.get("daily_digest")
    if not digest or not digest.summaries:
        state["loop2_continue"] = False
        return state

    client = _get_genai_client()
    model_name = state.get("model", DEFAULT_MODEL)
    editorial_retries = state.get("editorial_retry_count", 0)

    # Heuristic Coherence & Sense-Checking Guardrail
    red_flags = [
        "pagemeta",
        "canonical pointing",
        "earlier in the head",
        "duplicate of the homepage",
        "&#x",
        "content could not be extracted",
        "access denied",
        "please enable javascript",
    ]
    malformed_items: list[ArticleSummary] = []
    for s in digest.summaries:
        text_blob = (s.tldr + " " + " ".join(s.key_takeaways) + " " + s.technical_relevance).lower()
        if any(flag in text_blob for flag in red_flags) or any(len(t) < 15 for t in s.key_takeaways):
            malformed_items.append(s)

    if malformed_items and editorial_retries < MAX_EDITORIAL_RETRIES:
        clean_summaries = [s for s in digest.summaries if s not in malformed_items]
        state["summaries"] = clean_summaries if clean_summaries else digest.summaries
        state["editorial_retry_count"] = editorial_retries + 1
        state["editorial_feedback"] = "Removed malformed boilerplate items. Recompiling briefing with verified technical summaries."
        state["loop2_continue"] = True
        logger.info("Loop 2 active: Heuristic coherence check flagged %d malformed items, recompiling briefing (attempt %d/%d)",
                    len(malformed_items), state["editorial_retry_count"], MAX_EDITORIAL_RETRIES)
        return state

    if client:
        try:
            from google.genai import types
            prompt = (
                f"Review the assembled technical briefing for logical coherence, clarity, and developer relevance:\n\n"
                f"ARTICLE SUMMARIES:\n"
            )
            for idx, s in enumerate(digest.summaries, 1):
                prompt += f"{idx}. {s.title} ({s.source})\n   TL;DR: {s.tldr}\n   Takeaways: {json.dumps(s.key_takeaways)}\n   Discussion: {s.discussion_summary}\n\n"

            sys_instruction = (
                "You are the Principal Editorial Reviewer for developer-focused technical briefings.\n"
                "Note: By user design, there is no top-level executive summary; the briefing presents individual article cards.\n"
                "Audit the article summaries to ensure:\n"
                "1. The TL;DRs, main takeaways (2-3 bullets of 15-25 words), and developer discussion insights are accurate, clear, and relevant for senior software engineers.\n"
                "2. If the summaries meet these criteria, rate coherence_score >= 8 and is_relevant_for_developers=True.\n"
                "Return strict JSON matching EditorialVerificationResult."
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    response_mime_type="application/json",
                    response_schema=EditorialVerificationResult,
                    temperature=0.0,
                    seed=42,
                ),
            )
            result = EditorialVerificationResult.model_validate_json(response.text)

            if result.coherence_score < 7 and editorial_retries < MAX_EDITORIAL_RETRIES:
                state["editorial_retry_count"] = editorial_retries + 1
                state["editorial_feedback"] = result.editorial_feedback
                if result.refined_executive_overview:
                    state["refined_executive_overview"] = result.refined_executive_overview
                state["loop2_continue"] = True
                logger.info("Loop 2 active: Briefing coherence score %d/10 below threshold, triggering editorial recompilation (attempt %d/%d)",
                            result.coherence_score, state["editorial_retry_count"], MAX_EDITORIAL_RETRIES)
                return state
            else:
                state["loop2_continue"] = False
                logger.info("Loop 2 complete: Briefing coherence verified (score: %d/10, relevant for developers: %s)", result.coherence_score, result.is_relevant_for_developers)
                return state

        except Exception as e:
            logger.warning("Editorial coherence review failed, proceeding with current compilation: %s", e)

    state["loop2_continue"] = False
    return state


@node()
async def save_digest_node(state: dict[str, Any]) -> dict[str, Any]:
    """Write digest markdown to disk/GCS volume and atomically update seen_urls.json."""
    digest: DailyDigest = state.get("daily_digest")
    if not digest:
        raise ValueError("No daily_digest found in workflow state to save")

    today_str = digest.date
    digest_file = DIGESTS_DIR / f"{today_str}-digest.md"
    latest_file = DIGESTS_DIR / "latest.md"

    # Write markdown files atomically
    atomic_save_text(digest_file, digest.markdown_content)
    atomic_save_text(latest_file, digest.markdown_content)

    # Record seen URLs to prevent duplicate ingestion in future runs
    summarized_urls = [s.url for s in digest.summaries]
    record_seen_urls(SEEN_URLS_FILE, summarized_urls, RETENTION_DAYS)

    logger.info("Saved digest to %s and updated %s", digest_file, SEEN_URLS_FILE)
    state["saved_digest_path"] = str(digest_file)
    return state


# =====================================================================
# Workflow Graph Assembly & Execution
# =====================================================================

# Build ADK 2.0 Filter Agent
filter_agent = LlmAgent(
    name="filter_articles_agent",
    model=DEFAULT_MODEL,
    system_instruction="Curate candidate technical articles matching user interests into structured FilteredArticleList.",
    output_schema=FilteredArticleList,
)

# Build Root ADK 2.0 Workflow
root_agent = Workflow(
    name="tech_briefing_digest",
    edges=[
        (START, "fetch_feeds"),
        ("fetch_feeds", "filter_articles"),
        ("filter_articles", "extract_content"),
        ("extract_content", "summarize_article"),
        ("summarize_article", "verify_and_reflect_quality"),
        ("verify_and_reflect_quality", "filter_articles"),
        ("verify_and_reflect_quality", "compile_briefing"),
        ("compile_briefing", "verify_editorial_coherence"),
        ("verify_editorial_coherence", "compile_briefing"),
        ("verify_editorial_coherence", "save_digest"),
        ("save_digest", END),
    ],
)
root_agent.add_node("fetch_feeds", fetch_feeds_node)
root_agent.add_node("filter_articles", filter_articles_node)
root_agent.add_node("extract_content", extract_content_node)
root_agent.add_node("summarize_article", summarize_article_node)
root_agent.add_node("verify_and_reflect_quality", verify_and_reflect_quality_node)
root_agent.add_node("compile_briefing", compile_briefing_node)
root_agent.add_node("verify_editorial_coherence", verify_editorial_coherence_node)
root_agent.add_node("save_digest", save_digest_node)


async def execute_digest_workflow(
    interests: UserInterests | None = None,
    feeds: list[str] | None = None,
    force_refresh: bool = False,
    model: str = DEFAULT_MODEL,
) -> DailyDigest:
    """Execute the end-to-end Tech-Briefing Digest workflow with Session Short-Term Memory and Memory-Guided Adaptive Reflection."""
    state: dict[str, Any] = {
        "user_interests": interests or UserInterests(topics=DEFAULT_INTERESTS, max_articles=5),
        "feeds": feeds or DEFAULT_FEEDS,
        "force_refresh": force_refresh,
        "model": model,
        "session_memory": SessionShortTermMemory(),
        "editorial_retry_count": 0,
        "loop1_iteration": 0,
    }

    # Step 1: Fetch feeds & candidate deduplication (14-day freshness)
    state = await fetch_feeds_node(state)

    # Loop 1: Memory-Guided Adaptive Reflection Loop (Filter -> Extract -> Summarize -> Verify -> Filter...)
    while True:
        state = await filter_articles_node(state)
        state = await extract_content_node(state)
        state = await summarize_article_node(state)
        state = await verify_and_reflect_quality_node(state)
        if not state.get("loop1_continue", False):
            break

    # Loop 2: Briefing Compilation & Editorial Coherence Verification
    while True:
        state = await compile_briefing_node(state)
        state = await verify_editorial_coherence_node(state)
        if not state.get("loop2_continue", False):
            break

    # Step 3: Atomic storage & seen URLs tracking
    state = await save_digest_node(state)

    return state["daily_digest"]


async def summarize_single_alert(
    url: str | None = None,
    text: str | None = None,
    title: str | None = None,
    author: str | None = None,
    source: str = "webhook",
    model: str = DEFAULT_MODEL,
) -> ArticleSummary:
    """Summarize an individual incoming alert, tweet, or article URL on demand."""
    raw_content = ""
    resolved_title = title or "Inbound Notification"
    resolved_url = url or "https://inbound.alert/local"

    if url:
        raw_content = await safe_extract_webpage(url)
        clean_extracted = raw_content.replace("<untrusted_content>", "").replace("</untrusted_content>", "").strip()
        if not title and len(clean_extracted.split()) >= 3:
            first_line = clean_extracted.splitlines()[0][:100].strip()
            if first_line and not first_line.startswith("<"):
                resolved_title = first_line

    if text:
        if raw_content:
            raw_content = f"{text}\n\nLinked Content:\n{raw_content}"
        else:
            raw_content = text
        if not title:
            resolved_title = text.splitlines()[0][:80].strip()

    source_label = f"{source.title()} ({author})" if author else source.title()
    art = ArticleMetadata(
        title=resolved_title,
        url=resolved_url,
        source=source_label,
        score=100,
        comments_count=0,
        read_time="1 min read",
        is_webpage_only=len(raw_content.split()) < 150,
    )

    dummy_state = {
        "extracted_articles": [(art, raw_content)],
        "session_memory": SessionShortTermMemory(),
        "model": model,
    }
    summaries_state = await summarize_article_node(dummy_state)
    summaries = summaries_state.get("summarized_articles", [])
    if summaries:
        return summaries[0]

    # Deterministic fallback synthesis
    tldr, takeaways, relevance, is_tech = synthesize_technical_summary(
        title=resolved_title,
        text=raw_content,
        source=source_label,
        is_webpage_only=art.is_webpage_only,
    )
    return ArticleSummary(
        title=resolved_title,
        url=resolved_url,
        source=source_label,
        tldr=tldr or (raw_content[:200] if raw_content else "No content available."),
        key_takeaways=takeaways,
        quality_score=8,
        read_time="1 min read",
        has_genuine_technical_content=is_tech,
        is_webpage_only=art.is_webpage_only,
    )


