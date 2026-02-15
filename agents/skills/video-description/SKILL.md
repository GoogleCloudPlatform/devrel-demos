---
name: video-description
description: Generates optimized descriptions for video platforms from transcripts and supplementary material. Use when the user asks for a video description or provides a transcript for video preparation.
---

# Video Description

This skill helps you create engaging, platform-optimized video descriptions. It synthesizes information from a video transcript and any provided supplementary context (like a blog post or technical specifications).

## Sequential Workflow

Follow these steps to generate a high-quality description:

1. **Analyze Source Material**: Read the video transcript and any supplementary documents. Identify key topics, keywords, and calls to action.
2. **Determine Platform**: Identify the target platform (e.g., YouTube, Instagram, TikTok). If not specified, default to a general SEO-friendly format.
3. **Select Template**: Choose an appropriate template from [TEMPLATES.md](TEMPLATES.md) based on the video type and platform.
4. **Draft Description**: Create the description using the selected template.
    - **Point of View**: Always use first-person singular ("I", "my") instead of "we" or "our".
    - **Relevance**: Ensure the first few lines contain the most critical information and keywords.
5. **Add Metadata**: Include timestamps (if identifiable in the transcript), relevant links, and social CTA.
    - **Hashtags**: Limit to exactly 5 of the most relevant ones with broad appeal.
6. **Validate**: Run the [scripts/validate.py](scripts/validate.py) script to ensure the description meets platform-agnostic formatting standards.

## Reference Materials

- **Templates**: See [TEMPLATES.md](TEMPLATES.md) for standard formats and platform variations.
- **Examples**: See [EXAMPLES.md](EXAMPLES.md) for few-shot examples.
- **Validation**: Detailed rules in [scripts/validate.py](scripts/validate.py).
- **Regression Testing**: Run `pytest scripts/test_validate.py` to check performance against [evaluations.json](evaluations.json).
