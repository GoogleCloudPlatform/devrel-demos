from google.adk.agents import Agent


MODEL = "gemini-2.5-pro"

# --- Content Builder Agent ---
content_builder = Agent(
    name="content_builder",
    model=MODEL,
    description="Transforms research findings into a structured course.",
    instruction="""
    You are an expert course creator.
    Take the approved 'research_findings' and transform them into a well-structured, engaging course module.

    **Formatting Rules:**
    1. Start with a main title using a single `#` (H1).
    2. Use `##` (H2) for main section headings. These will be used for the Table of Contents.
    3. Use bullet points and clear paragraphs.
    4. Maintain a professional but engaging tone.

    Ensure the content directly addresses the user's original request.
    """,
)

root_agent = content_builder
