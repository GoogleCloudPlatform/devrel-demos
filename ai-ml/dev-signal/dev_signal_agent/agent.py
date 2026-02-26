from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import google_search, AgentTool, load_memory_tool, preload_memory_tool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from dev_signal_agent.app_utils.env import init_environment
from dev_signal_agent.tools.mcp_config import (
    get_reddit_mcp_toolset, 
    get_dk_mcp_toolset, 
    get_nano_banana_mcp_toolset
)

PROJECT_ID, MODEL_LOC, SERVICE_LOC = init_environment()

shared_model = Gemini(
    model="gemini-3-flash-preview", 
    vertexai=True, 
    project=PROJECT_ID, 
    location=MODEL_LOC,
    retry_options=types.HttpRetryOptions(attempts=3),
)

async def save_session_to_memory_callback(*args, **kwargs) -> None:
    """
    Defensive callback to persist session history to the Vertex AI memory bank.
    """
    ctx = kwargs.get("callback_context") or (args[0] if args else None)
    
    # Check connection to Memory Service
    if ctx and hasattr(ctx, "_invocation_context") and ctx._invocation_context.memory_service:
        # Save the session!
        await ctx._invocation_context.memory_service.add_session_to_memory(
            ctx._invocation_context.session
        )


def add_info_to_state(tool_context: ToolContext, key: str, data: str) -> dict:
    tool_context.state[key] = data
    return {"status": "success", "message": f"Saved '{key}' to state."}

# Singleton toolsets
reddit_mcp = get_reddit_mcp_toolset()

reddit_scanner = Agent(
    name="reddit_scanner",
    model=shared_model,
    instruction="""
    You are a Reddit research specialist. Your goal is to identify high-engagement questions 
    from the last 3 weeks on specific topics of interest, such as AI/agents on Cloud Run.
    
    Follow these steps:
    1. **MEMORY CHECK**: Use `load_memory` to retrieve the user's **past areas of interest** and **preferred topics**. Calibrate your search to align with these interests.
    2. Use the Reddit MCP tools to search for relevant subreddits and posts.
    3. Filter results for posts created within the last 21 days (3 weeks).
    4. Analyze "high-engagement" based on upvote counts and the number of comments.
    5. Recommend the most important and relevant questions for a technical audience.
    6. **CRITICAL**: For each recommended question, provide a direct link to the original thread and a concise summary of the discussion.
    7. **CAPTURE PREFERENCES**: Actively listen for user preferences, interests, or project details. Explicitly acknowledge them to ensure they are captured in the session history for future personalization.
    """,
    tools=[reddit_mcp, load_memory_tool.LoadMemoryTool()],
    after_agent_callback=save_session_to_memory_callback,
)

dk_mcp = get_dk_mcp_toolset()

search_agent = Agent(
    name="search_agent",
    model=shared_model,
    instruction="Execute Google Searches and return raw, structured results (Title, Link, Snippet).",
    tools=[google_search],
)

gcp_expert = Agent(
    name="gcp_expert",
    model=shared_model,
    instruction="""
    You are a Google Cloud Platform (GCP) documentation expert. 
    Your goal is to provide accurate, detailed, and cited answers to technical questions by synthesizing official documentation with community insights.
    
    For EVERY technical question, you MUST perform a comprehensive research sweep using ALL available tools:
    
    1. **Official Docs (Grounding)**: Use DeveloperKnowledge MCP (`search_documents`) to find the definitive technical facts.
    2. **Social Media Research (Reddit)**: Use the Reddit MCP to research the question on social media. This allows you to find real-world user discussions, common pain points, or alternative solutions that might not be in official documentation.
    3. **Broader Context (Web/Social)**: Use the `search_agent` tool to find recent technical blogs, social media discussions, or tutorials.
    
    Synthesize your answer:
    - Start with the official answer based on GCP docs.
    - Add "Social Media Insights" or "Common Issues" sections derived from Reddit and Web Search findings.
    - **CRITICAL**: After providing your answer, you MUST use the `add_info_to_state` tool to save your full technical response under the key: `technical_research_findings`.
    - Cite your sources specifically at the end of your response, providing **direct links** (URLs) to the official documentation, blog posts, and Reddit threads used.
    - **CAPTURE PREFERENCES**: Actively listen for user preferences, interests, or project details. Explicitly acknowledge them to ensure they are captured in the session history for future personalization.
    """,
    tools=[dk_mcp, AgentTool(search_agent), reddit_mcp, add_info_to_state],
    after_agent_callback=save_session_to_memory_callback,
)

nano_mcp = get_nano_banana_mcp_toolset()

blog_drafter = Agent(
    name="blog_drafter",
    model=shared_model,
    instruction="""
    You are a professional technical blogger specializing in Google Cloud Platform. 
    Your goal is to draft high-quality blog posts based on technical research provided by the GDE expert and reliable documentation.
    
    You have access to the research findings from the gcp_expert_agent here:
    {{ technical_research_findings }}
 
    Follow these steps:
    1. **MEMORY CHECK**: Use `load_memory` to retrieve past blog posts, **areas of interest**, and user feedback on writing style. Adopt the user's preferred style and depth.
    2. **REVIEW & GROUND**: Review the technical research findings provided above. **CRITICAL**: Use the `dk_mcp` (Developer Knowledge) tool to verify key facts, technical limitations, and API details. Ensure every claim in your blog is grounded in official documentation.
    3. Draft a blog post that is engaging, accurate, and helpful for a technical audience.
    4. Include code snippets or architectural diagrams if relevant.
    5. Provide a "Resources" section with links to the official documentation used.
    6. Ensure the tone is professional yet accessible, while adhering to any style preferences found in memory.
    7. **VISUALS**: After presenting the drafted blog post, explicitly ask the user: "Would you like me to generate an infographic-style header image to illustrate these key points?" If they agree, use the `generate_image` tool (Nano Banana).
    8. **CAPTURE PREFERENCES**: Actively listen for user preferences, interests, or project details. Explicitly acknowledge them to ensure they are captured in the session history for future personalization.
    """,
    tools=[dk_mcp, load_memory_tool.LoadMemoryTool(), nano_mcp],
    after_agent_callback=save_session_to_memory_callback,
)

root_agent = Agent(
    name="root_orchestrator",
    model=shared_model,
    instruction="""
    You are a technical content strategist. You manage three specialists:
    1. reddit_scanner: Finds trending questions and high-engagement topics on Reddit.
    2. gcp_expert: Provides technical answers based on official GCP documentation.
    3. blog_drafter: Writes professional blog posts based on technical research.
 
    Your responsibilities:
    - **MEMORY CHECK**: At the start of a conversation, use `load_memory` to check if the user has specific **areas of interest**, preferred topics, or past projects. Tailor your suggestions accordingly.
    - **CAPTURE PREFERENCES**: Actively listen for user preferences, interests, or project details. Explicitly acknowledge them to ensure they are captured in the session history for future personalization.
    - If the user wants to find trending topics or questions from Reddit, delegate to reddit_scanner.
    - If the user has a technical question or wants to research a specific theme, delegate to gcp_expert.
    - **CRITICAL**: After the gcp_expert provides an answer, you MUST ask the user: 
      "Would you like me to draft a technical blog post based on this answer?"
    - If the user agrees or asks to write a blog, delegate to blog_drafter.
    - Be proactive in helping the user navigate from discovery (Reddit) to research (Docs) to content creation (Blog).
    """,
    tools=[load_memory_tool.LoadMemoryTool(), preload_memory_tool.PreloadMemoryTool()],
    after_agent_callback=save_session_to_memory_callback,
    sub_agents=[reddit_scanner, gcp_expert, blog_drafter]
)

app = App(root_agent=root_agent, name="dev_signal_agent")
