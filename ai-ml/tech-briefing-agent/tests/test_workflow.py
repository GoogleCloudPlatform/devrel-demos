"""Tests for ADK 2.0 Workflow and schemas."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from digest_agent.agent import (
    compile_briefing_node,
    execute_digest_workflow,
    extract_content_node,
    fetch_feeds_node,
    filter_articles_node,
    root_agent,
    save_digest_node,
    summarize_article_node,
    verify_and_reflect_quality_node,
    verify_editorial_coherence_node,
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
    UserInterests,
)


class TestSchemas:
    """Test Pydantic schema validation and serialization."""

    def test_article_metadata_schema(self):
        art = ArticleMetadata(
            title="Modern Cloud Architecture",
            url="https://example.com/cloud",
            source="Tech Blog",
            published_at="2026-08-27T10:00:00Z",
            snippet="A deep dive into cloud patterns.",
            score=120,
            comments_count=45,
            is_verified=True,
        )
        assert art.title == "Modern Cloud Architecture"
        assert art.url == "https://example.com/cloud"
        assert art.score == 120
        assert art.comments_count == 45
        assert art.is_verified is True

    def test_user_interests_defaults(self):
        interests = UserInterests()
        assert interests.max_articles == 5
        assert isinstance(interests.topics, list)

    def test_filtered_article_list(self):
        art = ArticleMetadata(
            title="ADK 2.0 Released",
            url="https://example.com/adk",
            source="Google Cloud",
            published_at="2026-08-27T12:00:00Z",
        )
        filtered = FilteredArticleList(
            selected_articles=[art],
            reasoning="Matched AI Engineering topic."
        )
        assert len(filtered.selected_articles) == 1
        assert filtered.reasoning == "Matched AI Engineering topic."

    def test_daily_digest_schema(self):
        summary = ArticleSummary(
            title="Cloud Run Instances",
            url="https://cloud.google.com",
            source="GCP",
            key_takeaways=["Dedicated singleton", "GCS mount support"],
            technical_relevance="Enables stateful workloads on serverless pricing.",
            tldr="Cloud Run Instances adds persistent volume mounts.",
            score=300,
            comments_count=85,
            quality_score=9,
        )
        digest = DailyDigest(
            title="Daily Digest 2026-08-27",
            date="2026-08-27",
            summaries=[summary],
            markdown_content="# Daily Digest 2026-08-27\n...",
        )
        assert len(digest.summaries) == 1
        assert digest.date == "2026-08-27"
    def test_editorial_synthesis_and_verification_schemas(self):
        synthesis = EditorialSynthesis(
            executive_overview="Cloud platforms are converging on singleton stateful primitives.",
            key_themes=["Serverless Stateful Workflows", "ADK Graph Reflection"]
        )
        assert len(synthesis.key_themes) == 2
        assert "singleton" in synthesis.executive_overview

        verif = EditorialVerificationResult(
            is_coherent=True,
            coherence_score=9,
            editorial_feedback="",
            refined_executive_overview="Refined synthesis."
        )
        assert verif.is_coherent is True
        assert verif.coherence_score == 9


class TestWorkflowNodes:
    """Test individual ADK 2.0 workflow nodes and pipeline orchestration."""

    def test_workflow_graph_structure(self):
        """Verify root_agent graph has expected edges and nodes."""
        assert root_agent.name == "tech_briefing_digest"
        assert len(root_agent.edges) >= 8
        expected_nodes = {
            "fetch_feeds",
            "filter_articles",
            "extract_content",
            "summarize_article",
            "verify_and_reflect_quality",
            "compile_briefing",
            "verify_editorial_coherence",
            "save_digest",
        }
        for node_name in expected_nodes:
            assert node_name in root_agent._nodes

    @pytest.mark.asyncio
    async def test_fetch_feeds_node_deduplication(self, tmp_path: Path):
        art1 = ArticleMetadata(title="Building an AI Agent on Cloud Run", url="https://example.com/1", source="HN", published_at="2026-08-27", snippet="Agent architecture")
        art2 = ArticleMetadata(title="Distributed LLM Serving Architecture", url="https://example.com/2", source="HN", published_at="2026-08-27", snippet="LLM inference")

        with patch("digest_agent.agent.fetch_hn_top_stories", new_callable=AsyncMock) as mock_hn, \
             patch("digest_agent.agent.fetch_rss_feeds", new_callable=AsyncMock) as mock_rss, \
             patch("digest_agent.agent.load_and_prune_seen_urls") as mock_seen:

            mock_hn.return_value = [art1, art2]
            mock_rss.return_value = []
            mock_seen.return_value = {"https://example.com/1"}

            state = {"force_refresh": False}
            result_state = await fetch_feeds_node(state)

            candidates = result_state["candidate_articles"]
            assert len(candidates) == 1
            assert candidates[0].url == "https://example.com/2"

    @pytest.mark.asyncio
    async def test_filter_articles_node_fallback(self):
        art1 = ArticleMetadata(title="Intro to Go & Cloud Run", url="https://example.com/1", source="HN", published_at="2026-08-27", snippet="Go runtime")
        art2 = ArticleMetadata(title="Baking Sourdough", url="https://example.com/2", source="Blog", published_at="2026-08-27", snippet="Bread recipe")

        state = {
            "candidate_articles": [art1, art2],
            "user_interests": UserInterests(topics=["Go", "Cloud Run"], max_articles=1),
        }

        # Run without genai client (fallback mode)
        with patch("digest_agent.agent._get_genai_client", return_value=None):
            result_state = await filter_articles_node(state)
            filtered: FilteredArticleList = result_state["filtered_articles"]
            assert len(filtered.selected_articles) == 1
            assert filtered.selected_articles[0].title == "Intro to Go & Cloud Run"

    @pytest.mark.asyncio
    async def test_differential_summarization_and_loop1(self):
        from digest_agent.schemas import SessionShortTermMemory
        art1 = ArticleMetadata(title="Article 1", url="https://example.com/1", source="HN")
        art2 = ArticleMetadata(title="Article 2", url="https://example.com/2", source="HN")
        raw_text = "<untrusted_content>Valid substantive engineering content describing systems architecture and metrics in extensive detail across multiple cloud providers.</untrusted_content>"

        state = {
            "extracted_articles": [(art1, raw_text), (art2, raw_text)],
            "session_memory": SessionShortTermMemory(),
            "loop1_iteration": 0,
        }

        with patch("digest_agent.agent._get_genai_client", return_value=None), \
             patch("digest_agent.agent.verify_link_liveliness", return_value=True):
            state = await summarize_article_node(state)
            assert len(state["summaries"]) == 2

            # Art1 is high quality
            state["candidate_summaries"][0].quality_score = 8
            state["candidate_summaries"][0].has_genuine_technical_content = True
            state["candidate_summaries"][0].is_grounded_in_article = True

            # Mock a low score / rejection on art2 in reflection
            state["candidate_summaries"][1].quality_score = 4
            state["candidate_summaries"][1].has_genuine_technical_content = False

            state = await verify_and_reflect_quality_node(state)
            # Quota not met (only 1 approved, target 2 minimum), so loop1_continue is True
            assert state["loop1_continue"] is True
            assert "https://example.com/2" in state["session_memory"].rejected_urls
            assert len(state["session_memory"].approved_summaries) == 1

            # On pass 2 (iteration >= 1), loop completes
            state["loop1_iteration"] = 1
            state = await verify_and_reflect_quality_node(state)
            assert state["loop1_continue"] is False
            assert len(state["summaries"]) == 1

    @pytest.mark.asyncio
    async def test_verify_editorial_coherence_node_and_loop2(self):
        summary = ArticleSummary(
            title="Google ADK 2.0 Released",
            url="https://cloud.google.com/adk",
            source="Google Cloud",
            discussion_url="https://news.ycombinator.com/item?id=777",
            read_time="3 min read",
            published_at="August 27, 2026",
            key_takeaways=["Graph workflows", "Parallel workers"],
            technical_relevance="High relevance for AI systems engineers.",
            tldr="ADK 2.0 introduces graph workflows.",
        )
        digest = DailyDigest(
            title="Personal Tech Briefing",
            date="2026-08-27",
            executive_synthesis="Briefing overview.",
            summaries=[summary],
            markdown_content="# Briefing\n...",
        )
        state = {
            "daily_digest": digest,
            "editorial_retry_count": 0,
        }

        with patch("digest_agent.agent._get_genai_client", return_value=None), \
             patch("digest_agent.agent.verify_link_liveliness", return_value=True):
            state = await verify_editorial_coherence_node(state)
            assert state["loop2_continue"] is False

    @pytest.mark.asyncio
    async def test_link_verification_drops_dead_urls(self):
        from digest_agent.agent import verify_and_reflect_quality_node
        s_alive = ArticleSummary(
            title="Live Article",
            url="https://example.com/alive",
            source="News",
            key_takeaways=["Live takeaway."],
            technical_relevance="Systems",
            tldr="Live TLDR",
        )
        s_dead = ArticleSummary(
            title="Dead Article",
            url="https://example.com/dead",
            source="News",
            key_takeaways=["Dead takeaway."],
            technical_relevance="Systems",
            tldr="Dead TLDR",
        )
        state = {"summaries": [s_alive, s_dead]}

        async def mock_liveliness(url: str, *args, **kwargs):
            return "alive" in url

        with patch("digest_agent.agent.verify_link_liveliness", side_effect=mock_liveliness), \
             patch("digest_agent.agent._get_genai_client", return_value=None):
            result = await verify_and_reflect_quality_node(state)
            assert len(result["summaries"]) == 1
            assert result["summaries"][0].url == "https://example.com/alive"

    @pytest.mark.asyncio
    async def test_compile_briefing_node(self):
        summary = ArticleSummary(
            title="Google ADK 2.0 Released",
            url="https://cloud.google.com/adk",
            source="Google Cloud",
            discussion_url="https://news.ycombinator.com/item?id=777",
            read_time="3 min read",
            published_at="August 27, 2026",
            key_takeaways=["Graph workflows", "Parallel workers"],
            technical_relevance="High relevance for AI systems engineers.",
            tldr="ADK 2.0 introduces graph workflows.",
        )
        state = {"summaries": [summary]}
        result_state = await compile_briefing_node(state)

        digest: DailyDigest = result_state["daily_digest"]
        assert digest is not None
        assert "Google ADK 2.0 Released" in digest.markdown_content
        assert "Main Takeaways for Developers" in digest.markdown_content
        assert "Read Article / Webpage" in digest.markdown_content
        assert "Hacker News Discussion" in digest.markdown_content
        assert len(digest.summaries) == 1

    @pytest.mark.asyncio
    async def test_save_digest_node(self, tmp_path: Path):
        summary = ArticleSummary(
            title="Test Title",
            url="https://example.com/test",
            source="Test Source",
            discussion_url="https://news.ycombinator.com/item?id=999",
            read_time="2 min read",
            published_at="Aug 27, 2026",
            key_takeaways=["Point 1"],
            technical_relevance="Testing relevance",
            tldr="Testing tldr",
        )
        digest = DailyDigest(
            title="Test Digest",
            date="2026-08-27",
            summaries=[summary],
            markdown_content="# Test Digest Content",
        )

        with patch("digest_agent.agent.DIGESTS_DIR", tmp_path / "digests"), \
             patch("digest_agent.agent.SEEN_URLS_FILE", tmp_path / "state" / "seen_urls.json"):

            state = {"daily_digest": digest}
            result_state = await save_digest_node(state)

            saved_path = Path(result_state["saved_digest_path"])
            assert saved_path.exists()
            assert saved_path.read_text(encoding="utf-8") == "# Test Digest Content"

            latest_file = tmp_path / "digests" / "latest.md"
            assert latest_file.exists()
            assert latest_file.read_text(encoding="utf-8") == "# Test Digest Content"

    @pytest.mark.asyncio
    async def test_execute_digest_workflow_end_to_end(self, tmp_path: Path):
        art = ArticleMetadata(
            title="Cloud Run Instances Architecture",
            url="https://example.com/cloudrun-instances",
            source="Google Cloud",
            discussion_url="https://news.ycombinator.com/item?id=888",
            read_time="4 min read",
            published_at="2026-08-27T00:00:00Z",
            snippet="Persistent storage on singleton containers.",
        )
        long_body = (
            "<untrusted_content>"
            "Google Cloud Run Instances introduces dedicated singleton containers with direct Cloud Storage bucket volume mounts. "
            "This primitive provides guaranteed 1 instance compute for stateful agents, long-lived background workers, and embedded databases. "
            "Developers benefit from predictable baseline pricing of $5.70 per month for 1 vCPU and 1 GiB memory on shared vCPU with burst budgets. "
            "Continuous execution is supported for up to 7 days before graceful automatic restart, making it ideal for persistent AI agent workflows."
            "</untrusted_content>"
        )

        with patch("digest_agent.agent.fetch_hn_top_stories", new_callable=AsyncMock, return_value=[art]), \
             patch("digest_agent.agent.fetch_rss_feeds", new_callable=AsyncMock, return_value=[]), \
             patch("digest_agent.agent.safe_extract_webpage", new_callable=AsyncMock, return_value=long_body), \
             patch("digest_agent.agent._get_genai_client", return_value=None), \
             patch("digest_agent.agent.DIGESTS_DIR", tmp_path / "digests"), \
             patch("digest_agent.agent.SEEN_URLS_FILE", tmp_path / "state" / "seen_urls.json"):

            digest = await execute_digest_workflow(
                interests=UserInterests(topics=["Cloud Run"], max_articles=1),
                force_refresh=True,
            )

            assert isinstance(digest, DailyDigest)
            assert len(digest.summaries) == 1
            assert digest.summaries[0].title == "Cloud Run Instances Architecture"
            assert digest.summaries[0].discussion_url == "https://news.ycombinator.com/item?id=888"
            assert "Cloud Run Instances Architecture" in digest.markdown_content
            assert "Read Article / Webpage" in digest.markdown_content
            assert "Hacker News Discussion" in digest.markdown_content

    @pytest.mark.asyncio
    async def test_filter_articles_mandatory_hacker_news_guarantee(self):
        hn_art = ArticleMetadata(
            title="Show HN: A New Open Agent Orchestrator",
            url="https://news.ycombinator.com/item?id=9999",
            source="Hacker News",
            score=150,
            comments_count=40,
            published_at="2026-08-27",
            snippet="Open-source agent workflow engine for distributed cloud systems",
        )
        blog_art1 = ArticleMetadata(
            title="Building Cloud Native Microservices",
            url="https://simonwillison.net/entries/1",
            source="Simon Willison",
            score=10,
            published_at="2026-08-27",
            snippet="Cloud patterns",
        )
        blog_art2 = ArticleMetadata(
            title="Evaluating LLM Systems at Scale",
            url="https://latent.space/entries/2",
            source="Latent Space",
            score=10,
            published_at="2026-08-27",
            snippet="Evaluation frameworks",
        )

        state = {
            "candidate_articles": [blog_art1, blog_art2, hn_art],
            "user_interests": UserInterests(topics=["AI Agents", "Cloud"], max_articles=2),
        }

        with patch("digest_agent.agent._get_genai_client", return_value=None):
            result_state = await filter_articles_node(state)
            selected = result_state["filtered_articles"].selected_articles
            # Must include at least 1 Hacker News item
            assert any("hacker news" in a.source.lower() for a in selected)
            assert any(a.title == "Show HN: A New Open Agent Orchestrator" for a in selected)

