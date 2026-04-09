from google.adk.agents import Agent


MODEL = "gemini-3-flash-preview"

# --- Researcher Agent ---
researcher = Agent(
    name="researcher",
    model=MODEL,
    description="Gathers information on a topic using Google Search.",
    instruction="""
    You are an expert researcher. Your goal is to find comprehensive and accurate information on the user's topic.
    Summarize your findings clearly.
    If you receive feedback that your research is insufficient, use the feedback to refine your next search.
    DO NOT output any function calls. Provide your research directly as text.
    """,
)

root_agent = researcher

