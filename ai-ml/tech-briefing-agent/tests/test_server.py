"""Unit tests for FastAPI endpoints and concurrency controls."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from digest_agent.schemas import ArticleSummary, DailyDigest
from digest_agent.server import app, workflow_mutex

client = TestClient(app)


def test_healthz_endpoint():
    """Verify health check endpoint returns 200 OK and valid status."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "digest-agent"
    assert "timestamp" in data
    assert "storage_ready" in data


def test_get_latest_view_empty(tmp_path: Path):
    """Verify /digest/latest returns friendly empty page if no digests exist."""
    with patch("digest_agent.server.DIGESTS_DIR", tmp_path / "digests"):
        response = client.get("/digest/latest")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "No Digests Available Yet" in response.text


def test_get_latest_view_with_content(tmp_path: Path):
    """Verify /digest/latest renders HTML from latest.md."""
    digests_dir = tmp_path / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    (digests_dir / "latest.md").write_text("# Latest Briefing\n- Point 1", encoding="utf-8")

    with patch("digest_agent.server.DIGESTS_DIR", digests_dir):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Latest Briefing" in response.text
        assert "Point 1" in response.text


def test_list_digests(tmp_path: Path):
    """Verify /api/digests returns list of files."""
    digests_dir = tmp_path / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    (digests_dir / "2026-08-27-digest.md").write_text("# Digest 1", encoding="utf-8")
    (digests_dir / "2026-08-26-digest.md").write_text("# Digest 2", encoding="utf-8")

    with patch("digest_agent.server.DIGESTS_DIR", digests_dir):
        response = client.get("/api/digests")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        filenames = [d["filename"] for d in data["digests"]]
        assert "2026-08-27-digest.md" in filenames
        assert "2026-08-26-digest.md" in filenames


def test_get_specific_digest(tmp_path: Path):
    """Verify /api/digest/{filename} retrieves markdown content or 404."""
    digests_dir = tmp_path / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    (digests_dir / "2026-08-27-digest.md").write_text("# Specific Digest Content", encoding="utf-8")

    with patch("digest_agent.server.DIGESTS_DIR", digests_dir):
        # Existing file
        resp = client.get("/api/digest/2026-08-27-digest.md")
        assert resp.status_code == 200
        assert resp.json()["markdown_content"] == "# Specific Digest Content"

        # Missing file
        missing = client.get("/api/digest/2020-01-01-digest.md")
        assert missing.status_code == 404


def test_generate_endpoint_success():
    """Verify POST /api/generate triggers workflow under lock."""
    dummy_digest = DailyDigest(
        title="Personal Tech Briefing - 2026-08-27",
        date="2026-08-27",
        summaries=[
            ArticleSummary(
                title="Google ADK 2.0",
                url="https://cloud.google.com/adk",
                source="GCP",
                key_takeaways=["Graph engine"],
                technical_relevance="Relevant",
                tldr="TLDR",
            )
        ],
        markdown_content="# Personal Tech Briefing\n...",
    )

    with patch("digest_agent.server.execute_digest_workflow", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = dummy_digest

        response = client.post(
            "/api/generate",
            json={"topics": ["Python", "ADK"], "max_articles": 3, "force_refresh": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["articles_summarized"] == 1
        assert data["title"] == "Personal Tech Briefing - 2026-08-27"
        assert data["markdown_length"] > 0


def test_html_rendering_with_badges_and_hn(tmp_path: Path):
    """Verify HTML rendering outputs orange Hacker News badge, pills, and action bar."""
    sample_md = (
        "# Personal Tech-Briefing Digest\n\n"
        "## 1. [HTTPX2 Python Client](https://github.com/pydantic/httpx2)\n"
        "**Source:** Hacker News • **Read time:** 1 min read • **Engagement:** 🔥 78 pts • **Published:** Aug 28, 2026 • 🛡️ *Verified Source*\n\n"
        "**Links:** [Read Original Article](https://github.com/pydantic/httpx2) • [Discussion Thread 💬 (27 comments)](https://news.ycombinator.com/item?id=49477157)\n\n"
        "> **TL;DR:** Next-generation HTTP client.\n\n"
        "#### Key Technical Takeaways\n"
        "- Supports HTTP/2.\n"
    )
    digests_dir = tmp_path / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    (digests_dir / "latest.md").write_text(sample_md, encoding="utf-8")

    with patch("digest_agent.server.DIGESTS_DIR", digests_dir):
        response = client.get("/digest/latest")
        assert response.status_code == 200
        html_out = response.text
        # Assert Hacker News badge
        assert 'badge-hn' in html_out
        assert 'Hacker News' in html_out
        # Assert action buttons
        assert 'btn-primary' in html_out
        assert 'Read Original Article' in html_out
        assert 'Discussion Thread' in html_out
        assert 'Copy Link' in html_out


@pytest.mark.asyncio
async def test_generate_endpoint_mutex_conflict():
    """Verify 409 Conflict is returned when workflow mutex is already locked."""
    async with workflow_mutex:
        response = client.post("/api/generate", json={})
        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"]
