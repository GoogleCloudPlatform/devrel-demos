"""Pydantic schemas for Personal Tech-Briefing Digest Agent."""

from pydantic import BaseModel, Field


class ArticleMetadata(BaseModel):
    """Metadata representing an ingested candidate article from RSS or Hacker News."""
    title: str = Field(..., description="Title of the article")
    url: str = Field(..., description="Canonical URL of the article")
    source: str = Field(..., description="Source origin (e.g. Hacker News, Google Cloud, AWS News, GitHub Blog, Martin Fowler)")
    published_at: str = Field(default="", description="Publication ISO timestamp or human-readable date")
    snippet: str = Field(default="", description="Snippet, summary, or description from the feed")
    discussion_url: str | None = Field(default=None, description="Link to discussion thread (e.g. Hacker News item URL or comments link)")
    read_time: str = Field(default="3 min read", description="Estimated reading time (e.g. '3 min read')")
    score: int = Field(default=0, description="Community engagement score/upvotes (e.g. Hacker News points)")
    comments_count: int = Field(default=0, description="Community discussion comments count")
    comments_text: list[str] = Field(default_factory=list, description="Top comments extracted from the discussion thread")
    importance_score: float = Field(default=0.0, description="Calculated importance score based on engagement and topic fit")
    is_verified: bool = Field(default=True, description="Whether the canonical URL was verified as active/reachable")
    has_full_article_content: bool = Field(default=True, description="Whether article body was successfully extracted (>= 50 words)")
    is_webpage_only: bool = Field(default=False, description="Whether the URL is a tool/project launch page or repo rather than a full long-form article")


class UserInterests(BaseModel):
    """User profile defining technical topics of interest and max briefing size."""
    topics: list[str] = Field(
        default_factory=lambda: [
            "AI Agents & Multi-Agent Frameworks",
            "Agent Development Kit (ADK) & Agentic Workflows",
            "Cloud AI Infrastructure & Serving",
            "Agent Reflection, Tool Calling & RAG",
            "Cloud Agent Security & Sandboxing",
        ],
        description="Target technical topics and keywords focusing on AI Agents and Cloud Applications"
    )
    max_articles: int = Field(default=5, description="Maximum number of articles to select for the digest (up to 5)")
    min_score: int = Field(default=20, description="Minimum community engagement score for candidate consideration")


class FilteredArticleList(BaseModel):
    """LLM selection output containing the most relevant articles for the user."""
    selected_articles: list[ArticleMetadata] = Field(
        default_factory=list,
        description="List of selected articles matching the user's technical interests and engagement criteria"
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of why these articles were selected over others"
    )


class QualityEvaluationItem(BaseModel):
    """Quality, relevance, and grounding reflection score for an individual summary."""
    url: str = Field(..., description="Article URL matching the summary")
    quality_score: int = Field(
        default=8,
        ge=1,
        le=10,
        description="Rating from 1 to 10 for technical depth, relevance to software engineers, and freshness"
    )
    is_relevant_to_engineer: bool = Field(
        default=True,
        description="Whether this content is genuinely informative and relevant to a software engineer"
    )
    is_technically_relevant: bool = Field(
        default=True,
        description="Whether the article contains genuine software/systems engineering substance rather than legal/DMCA/policy drama"
    )
    is_grounded: bool = Field(
        default=True,
        description="Whether summary and technical relevance accurately reflect source article without hallucination or generic boilerplate"
    )
    should_drop: bool = Field(
        default=False,
        description="Whether this article must be dropped completely due to lack of technical substance, paywalls, or boilerplate relevance"
    )
    needs_refinement: bool = Field(
        default=False,
        description="Whether this summary lacks sufficient technical depth, has vague claims, or needs re-summarization"
    )
    feedback_notes: str = Field(
        default="",
        description="Actionable critique for the summarizer explaining specifically what details or architectural depth to add"
    )
    quality_rationale: str = Field(
        default="",
        description="Brief rationale assessing technical substance and avoiding fluff"
    )


class QualityBatchEvaluation(BaseModel):
    """Batch reflection evaluation across all candidate summaries."""
    evaluations: list[QualityEvaluationItem] = Field(
        default_factory=list,
        description="Evaluations for each candidate article summary"
    )
    overall_briefing_assessment: str = Field(
        default="",
        description="Overall reflection on the quality, balance, and relevance of the batch"
    )


class EditorialSynthesis(BaseModel):
    """Structured editorial overview and overarching architectural themes across all summarized articles."""
    executive_overview: str = Field(
        ...,
        description="A cohesive 2-3 paragraph synthesis explaining overarching industry themes, trade-offs, and shifts across today's articles"
    )
    key_themes: list[str] = Field(
        default_factory=list,
        description="2 to 3 core overarching architectural or systems themes identified across the batch"
    )


class EditorialVerificationResult(BaseModel):
    """Editorial sense-check and coherence validation result."""
    is_coherent: bool = Field(
        default=True,
        description="Whether the entire briefing makes logical technical sense, has non-contradictory takeaways, and forms a cohesive narrative"
    )
    is_relevant_for_developers: bool = Field(
        default=True,
        description="Whether the entire briefing and retained articles provide genuine technical value to software developers and cloud architects"
    )
    coherence_score: int = Field(
        default=8,
        ge=1,
        le=10,
        description="Editorial coherence rating (1 to 10) for clarity, logic, and technical depth"
    )
    editorial_feedback: str = Field(
        default="",
        description="Specific critique if the executive summary or takeaways are disjointed, contradictory, or need rewriting"
    )
    refined_executive_overview: str = Field(
        default="",
        description="Refined or polished executive overview addressing the editorial critique"
    )


class ArticleSummary(BaseModel):
    """Structured deep-dive summary for an individual article answering 3 core developer questions."""
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL (direct link to original article/blog post)")
    source: str = Field(..., description="Clean source name (e.g. Hacker News, AWS News, GitHub Blog, Google Cloud, Martin Fowler)")
    discussion_url: str | None = Field(
        default=None,
        description="Link to discussion thread (e.g. Hacker News item URL or source feed discussion)"
    )
    read_time: str = Field(
        default="3 min read",
        description="Estimated reading time (e.g. '3 min read')"
    )
    published_at: str = Field(
        default="",
        description="Formatted publication timestamp"
    )
    score: int = Field(
        default=0,
        description="Community engagement points/upvotes"
    )
    comments_count: int = Field(
        default=0,
        description="Community discussion comments count"
    )
    is_verified: bool = Field(
        default=True,
        description="Whether links were checked and verified active"
    )
    quality_score: int = Field(
        default=8,
        description="Reflected technical quality score (1-10)"
    )
    quality_rationale: str = Field(
        default="",
        description="Reflected evaluation rationale"
    )
    feedback_notes: str = Field(
        default="",
        description="Critique notes received from previous reflection pass"
    )
    refinement_count: int = Field(
        default=0,
        description="Number of re-summarization iterations performed"
    )
    tldr: str = Field(
        ...,
        description="Crisp 1-2 sentence executive summary of what the system/tool/architecture does and the problem it solves (no templates)"
    )
    key_takeaways: list[str] = Field(
        default_factory=list,
        description="2 to 4 bullet points detailing concrete architectural mechanisms, design decisions, benchmarks, or systems trade-offs"
    )
    discussion_summary: str = Field(
        default="",
        description="Synthesized summary of practical developer experiences, debated trade-offs, criticisms, and consensus from comments (no prefixes)"
    )
    technical_relevance: str = Field(
        default="",
        description="Legacy technical relevance field (optional)"
    )
    has_genuine_technical_content: bool = Field(
        default=True,
        description="Whether the article contains real engineering/architectural systems specifics"
    )
    is_grounded_in_article: bool = Field(
        default=True,
        description="Whether takeaways and relevance directly reflect the source text without hallucination"
    )
    is_webpage_only: bool = Field(
        default=False,
        description="Whether the URL is a tool/project launch page or repo rather than a full long-form article"
    )


class SessionShortTermMemory(BaseModel):
    """Session short-term memory passed through the Loop 1 cycle."""
    approved_summaries: list[ArticleSummary] = Field(
        default_factory=list,
        description="Accumulated high-quality approved article summaries"
    )
    rejected_urls: list[str] = Field(
        default_factory=list,
        description="URLs rejected due to inaccessibility, non-technical content, or poor quality"
    )
    rejected_articles: list[dict] = Field(
        default_factory=list,
        description="Detailed record [{url, title, reason, phase}] for rejected items"
    )
    filter_guidance: list[str] = Field(
        default_factory=list,
        description="Critique instructing filter_articles on what categories/patterns to avoid"
    )
    extraction_notes: list[str] = Field(
        default_factory=list,
        description="Notes on inaccessible domains, paywalls, or parsing failures"
    )
    summarization_critique: list[str] = Field(
        default_factory=list,
        description="Direct instructions for the summarizer (e.g. demand concrete mechanisms, omit generic boilerplate)"
    )
    iteration_count: int = 0


class DailyDigest(BaseModel):
    """Aggregated briefing document containing all summaries and generated markdown."""
    title: str = Field(..., description="Digest title (e.g., 'Daily Tech Briefing - 2026-08-27')")
    date: str = Field(..., description="ISO date format (YYYY-MM-DD)")
    executive_synthesis: str = Field(
        default="",
        description="Synthesized editorial overview connecting broader industry themes"
    )
    summaries: list[ArticleSummary] = Field(
        default_factory=list,
        description="List of article summaries included in this briefing (2 to 5 articles)"
    )
    markdown_content: str = Field(
        ...,
        description="Rendered Markdown content of the complete digest briefing"
    )
