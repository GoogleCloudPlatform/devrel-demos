"""Unit tests for utility functions in digest_agent.utils."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from digest_agent.schemas import ArticleMetadata
from digest_agent.utils import (
    atomic_save_json,
    fetch_hn_top_stories,
    fetch_rss_feeds,
    is_safe_url,
    load_and_prune_seen_urls,
    record_seen_urls,
    safe_extract_webpage,
)


class TestSSRFValidation:
    """Test SSRF validation logic against cloud metadata, loopback, private subnets, and schemes."""

    @pytest.mark.parametrize(
        "unsafe_url",
        [
            "http://169.254.169.254/computeMetadata/v1/",
            "http://169.254.169.254",
            "https://169.254.169.254/latest/meta-data/",
            "http://127.0.0.1",
            "http://127.0.0.1:8080/secret",
            "http://127.1.2.3/",
            "http://localhost",
            "http://localhost:3000",
            "http://[::1]/",
            "http://[::ffff:169.254.169.254]/",
            "http://[::ffff:127.0.0.1]/",
            "http://10.0.0.1/admin",
            "http://10.255.255.255/",
            "http://172.16.0.1/internal",
            "http://172.31.255.255/",
            "http://192.168.1.1/router",
            "http://169.254.10.20/",
            "file:///etc/passwd",
            "ftp://files.example.com",
            "gopher://127.0.0.1:70",
            "",
            None,
        ],
    )
    def test_unsafe_urls_blocked(self, unsafe_url: str | None):
        assert is_safe_url(unsafe_url) is False

    @pytest.mark.parametrize(
        "safe_url",
        [
            "https://cloud.google.com/blog",
            "https://news.ycombinator.com/item?id=12345",
            "https://github.blog/feed/",
            "https://aws.amazon.com/blogs/aws/",
            "https://martinfowler.com/articles/serverless.html",
        ],
    )
    def test_safe_urls_allowed(self, safe_url: str):
        assert is_safe_url(safe_url) is True


class TestAtomicFilePersistence:
    """Test atomic file writing and GCS volume mount safety."""

    def test_atomic_save_json(self, tmp_path: Path):
        target = tmp_path / "subdir" / "data.json"
        payload = {"key": "value", "list": [1, 2, 3], "unicode": "🚀"}

        atomic_save_json(target, payload)

        assert target.exists()
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == payload

        # Check no temporary files were left behind
        tmp_files = list(target.parent.glob(".*.tmp"))
        assert len(tmp_files) == 0

    def test_atomic_save_overwrites_existing(self, tmp_path: Path):
        target = tmp_path / "state.json"
        atomic_save_json(target, {"version": 1})
        atomic_save_json(target, {"version": 2})

        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == {"version": 2}


class TestSeenUrlPruning:
    """Test seen URL persistence and TTL retention pruning."""

    def test_load_and_prune_seen_urls(self, tmp_path: Path):
        seen_file = tmp_path / "seen_urls.json"
        now = datetime.now(timezone.utc)

        active_url = "https://example.com/recent"
        old_url = "https://example.com/expired"

        data = {
            active_url: (now - timedelta(days=5)).isoformat(),
            old_url: (now - timedelta(days=40)).isoformat(),
        }
        atomic_save_json(seen_file, data)

        seen_set = load_and_prune_seen_urls(seen_file, retention_days=30)
        assert active_url in seen_set
        assert old_url not in seen_set

        # Verify disk state was pruned
        with open(seen_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        assert active_url in disk_data
        assert old_url not in disk_data

    def test_record_seen_urls(self, tmp_path: Path):
        seen_file = tmp_path / "seen_urls.json"
        new_urls = ["https://example.com/1", "https://example.com/2"]

        record_seen_urls(seen_file, new_urls, retention_days=30)
        seen_set = load_and_prune_seen_urls(seen_file, retention_days=30)

        assert "https://example.com/1" in seen_set
        assert "https://example.com/2" in seen_set


class TestContentExtraction:
    """Test SSRF-safe content extraction."""

    @pytest.mark.asyncio
    async def test_safe_extract_blocks_metadata(self):
        result = await safe_extract_webpage("http://169.254.169.254/latest/meta-data/")
        assert "<untrusted_content>" in result
        assert "[Blocked:" in result

    @pytest.mark.asyncio
    async def test_safe_extract_wraps_in_delimiters(self):
        mock_html = "<html><body><h1>Architecture Digest</h1><p>Cloud Run Instances are great.</p></body></html>"
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.is_redirect = False
            mock_response.text = mock_html
            mock_get.return_value = mock_response

            result = await safe_extract_webpage("https://example.com/article-1")
            assert result.startswith("<untrusted_content>")
            assert result.endswith("</untrusted_content>")
            assert "Architecture Digest" in result or "Cloud Run" in result


class TestFeedFetching:
    """Test Hacker News and RSS feed fetching with mocked network calls."""

    @pytest.mark.asyncio
    async def test_fetch_hn_top_stories(self):
        with patch("httpx.AsyncClient.get") as mock_get:
            # First call for top stories, second for item
            top_resp = MagicMock()
            top_resp.status_code = 200
            top_resp.json.return_value = [101]
            top_resp.raise_for_status = MagicMock()

            item_resp = MagicMock()
            item_resp.status_code = 200
            item_resp.json.return_value = {
                "type": "story",
                "title": "Google ADK 2.0 Released",
                "url": "https://google.com/adk-2",
                "time": int(datetime.now(timezone.utc).timestamp()),
                "score": 250,
            }

            mock_get.side_effect = [top_resp, item_resp]

            articles = await fetch_hn_top_stories(limit=1)
            assert len(articles) == 1
            assert articles[0].title == "Google ADK 2.0 Released"
            assert articles[0].source == "Hacker News"
            assert articles[0].url == "https://google.com/adk-2"
            assert articles[0].discussion_url == "https://news.ycombinator.com/item?id=101"
            assert articles[0].published_at != ""
            assert "min read" in articles[0].read_time

    @pytest.mark.asyncio
    async def test_fetch_rss_feeds(self):
        sample_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Google Cloud Blog</title>
                <item>
                    <title>Cloud Run Instances Launched</title>
                    <link>https://cloud.google.com/blog/instances</link>
                    <comments>https://cloud.google.com/blog/instances#comments</comments>
                    <pubDate>Thu, 27 Aug 2026 12:00:00 GMT</pubDate>
                    <description>Singleton containers with persistent volume mounts for reliable background workers.</description>
                </item>
            </channel>
        </rss>"""

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = sample_rss
            mock_get.return_value = mock_resp

            articles = await fetch_rss_feeds(["https://cloud.google.com/blog/rss.xml"])
            assert len(articles) == 1
            assert articles[0].title == "Cloud Run Instances Launched"
            assert "cloud.google.com" in articles[0].url
            assert articles[0].source == "Google Cloud"
            assert articles[0].discussion_url == "https://cloud.google.com/blog/instances#comments"
            assert "2026" in articles[0].published_at
            assert "min read" in articles[0].read_time


class TestHelperFormatting:
    def test_estimate_read_time(self):
        from digest_agent.utils import estimate_read_time
        assert estimate_read_time("") == "3 min read"
        short_text = " ".join(["word"] * 50)
        assert estimate_read_time(short_text) == "1 min read"
        long_text = " ".join(["word"] * 600)
        assert estimate_read_time(long_text) == "3 min read"

    def test_clean_source_name(self):
        from digest_agent.utils import clean_source_name
        assert clean_source_name("Hacker News Top", "https://news.ycombinator.com") == "Hacker News"
        assert clean_source_name("AWS Architecture Blog", "https://aws.amazon.com/blogs/aws/") == "AWS News"
        assert clean_source_name(None, "https://github.blog/2026-08-27") == "GitHub Blog"
        assert clean_source_name(None, "https://martinfowler.com/articles/architecture.html") == "Martin Fowler"
        assert clean_source_name(None, "https://cloud.google.com/blog") == "Google Cloud"

    def test_format_timestamp(self):
        from digest_agent.utils import format_timestamp
        assert format_timestamp(1756296000) != ""
        assert format_timestamp("Thu, 27 Aug 2026 12:00:00 GMT") != ""


class TestTechnicalSynthesis:
    def test_is_genuinely_technical(self):
        from digest_agent.utils import is_genuinely_technical

        # Non-technical complaints & consumer rants
        is_tech, reason = is_genuinely_technical(
            "It works better in the app",
            text="I wanted to subscribe to an events calendar. It kept prompting me to download the mobile app. The web experience is broken and annoying.",
            snippet="Why websites force you to install their mobile apps instead of letting you use desktop browsers."
        )
        assert not is_tech
        assert "Non-technical consumer complaint" in reason

        # DMCA / Legal / Drama
        is_tech, reason = is_genuinely_technical(
            "GitHub repository taken down after DMCA copyright strike",
            snippet="A DMCA takedown notice was served to GitHub regarding an emulation project."
        )
        assert not is_tech

        # Genuine technical systems / engineering article
        is_tech, reason = is_genuinely_technical(
            "Optimizing Distributed Raft Consensus in Rust",
            text="We redesigned our Raft log replication engine using zero-copy memory buffers and io_uring in Linux kernel 6.x. Throughput increased by 3.5x while p99 latency dropped from 12ms to 2.8ms.",
            snippet="Deep dive into zero-copy networking, async Rust runtime benchmarks, and lock-free concurrency queues."
        )
        assert is_tech
        assert "technical" in reason.lower() or "engineering" in reason.lower()

    def test_summarize_discussion_comments_no_boilerplate_prefix(self):
        from digest_agent.utils import summarize_discussion_comments

        comments = [
            "User1: We benchmarked this in production and observed a 40% memory reduction with io_uring.",
            "User2: The main trade-off is kernel version compatibility and debugging complexity with async queues.",
            "User3: Agreed, especially when handling graceful reconnects during network partitions."
        ]
        summary = summarize_discussion_comments(comments)
        assert summary != ""
        # Must not contain the forbidden boilerplate prefix
        assert "Community discussion highlights" not in summary
        assert "key trade-offs" not in summary.lower() or "io_uring" in summary

    def test_synthesize_technical_summary_avoids_line_zero_copy(self):
        from digest_agent.utils import synthesize_technical_summary

        title = "Designing High-Throughput Stream Processing with Apache Flink"
        text = (
            "Streaming architectures have evolved significantly over the past decade. "
            "In this post, we introduce a new stateful operator topology utilizing RocksDB memory-mapped state backends. "
            "By tuning the checkpointing intervals and buffer pool allocations, we eliminated backpressure under 100k events/sec. "
            "Our benchmark demonstrates sub-second end-to-end latency across a 10-node Kubernetes cluster."
        )
        tldr, takeaways, relevance, has_tech = synthesize_technical_summary(title, text, "Hacker News")
        assert has_tech
        # TLDR should not be a blind copy-paste of sentence 0
        assert tldr != "Streaming architectures have evolved significantly over the past decade."
        assert len(takeaways) >= 2
        assert "RocksDB" in " ".join(takeaways) or "Flink" in tldr or "Apache Flink" in relevance
        assert len(relevance) > 10

    def test_is_genuinely_technical_rejects_minor_release_notes(self):
        from digest_agent.utils import is_genuinely_technical

        assert not is_genuinely_technical("llm-anthropic 0.27")[0]
        assert not is_genuinely_technical("datasette 1.0a8 release notes")[0]
        assert not is_genuinely_technical("v1.2.3 released")[0]
        assert not is_genuinely_technical("Quoting Paul Dix on time series databases")[0]
        assert not is_genuinely_technical("Why I hate Apple App Store policies")[0]

        # Valid technical essays should pass
        assert is_genuinely_technical("Building Autonomous Multi-Agent Workflows with ADK 2.0")[0]
        assert is_genuinely_technical("Deploying Scalable LLM Inference on Kubernetes with vLLM")[0]

    def test_synthesize_webpage_only_omits_takeaways(self):
        from digest_agent.utils import synthesize_technical_summary

        title = "Show HN: FastKV - An in-memory cache written in Rust"
        text = "FastKV is a simple in-memory key-value cache with sub-millisecond latency."
        tldr, takeaways, relevance, has_tech = synthesize_technical_summary(
            title, text, "Hacker News", is_webpage_only=True
        )
    def test_canonicalize_url(self):
        from digest_agent.utils import canonicalize_url

        url1 = "https://www.Example.com/blog/post-1/?utm_source=twitter&utm_medium=social#heading"
        url2 = "http://example.com/blog/post-1?ref=hn"
        assert canonicalize_url(url1) == "https://example.com/blog/post-1"
        assert canonicalize_url(url2) == "http://example.com/blog/post-1"

        # Trailing slash normalization
        assert canonicalize_url("https://example.com/path/") == "https://example.com/path"

    def test_compute_deterministic_relevance_score(self):
        from digest_agent.utils import compute_deterministic_relevance_score

        # AI & Agent story
        score, ok, reason = compute_deterministic_relevance_score(
            title="Building Autonomous Multi-Agent Workflows with MCP and ADK",
            snippet="Deep dive into tool use, reasoning evals, and agent architectures.",
            url="https://simonwillison.net/2026/agents",
            score=150,
            comments_count=45,
        )
        assert ok
        assert score > 50.0

        # Non-technical story
        score, ok, reason = compute_deterministic_relevance_score(
            title="Why I hate subscription price increases",
            snippet="Rant about streaming services raising prices.",
            url="https://example.com/rant",
            score=300,
            comments_count=200,
        )
        assert not ok
        assert score < 0



