import asyncio
import os
from dotenv import load_dotenv
from google.genai import types

from google.adk.agents import Agent
from google.adk.tools import agent_tool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams

from finwise.agents.analyst_agent import create_analyst_agent
from finwise.tools.stock_price_tool import get_stock_price
from finwise.tools.trading_tool import execute_trade

# --- Environment and Constants ---
load_dotenv()
# TODO: For testing only. Remove this line and use a .env file for production.
os.environ["GOOGLE_API_KEY"] = "GOOGLE_API_KEY"

APP_NAME = "finwise_analyst"
USER_ID = "user_analyst"
SESSION_ID = "session_analyst"
GEMINI_MODEL = "gemini-2.0-flash"

# --- Main Agent Definition ---
async def get_agent_and_toolset():
    """Asynchronously creates the main FinWise agent and its toolset."""
    analyst_agent = create_analyst_agent()

    portfolio_optimizer_toolset = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params={
                'command': 'python',
                'args': ["-m", "finwise.services.portfolio_optimizer_service"],
            }
        )
    )

    tools = [
        get_stock_price,
        execute_trade,
        agent_tool.AgentTool(agent=analyst_agent),
        portfolio_optimizer_toolset,
    ]

    agent = Agent(
        name="FinWiseAgent",
        model=GEMINI_MODEL,
        instruction="""You are FinWise, a personal finance and investment analyst.
Your primary instruction is to process requests in a strict, step-by-step manner. You must respond to the user after completing each step.

For the user's initial request, your first task is always to analyze.

The required sequence is:
1.  **Analyze**: Use the `AnalystAgent` to analyze the user's portfolio and report on your findings. If asked to plot, describe the plot you would make.
2.  **Optimize**: After reporting the analysis, use the `run_portfolio_optimization` tool to get a recommended allocation.
3.  **Price**: After presenting the allocation, use the `get_stock_price` tool for the top recommended stock.
4.  **Confirm**: After presenting the price, ask the user for confirmation before using the `execute_trade_logic` tool.""",
        description="The root agent for financial analysis and trading.",
        tools=tools,
    )
    
    return agent, portfolio_optimizer_toolset

async def run_finwise_and_get_final_response(prompt: str):
    """Initializes and runs the FinWise agent, returning only the final text response."""
    agent, toolset = await get_agent_and_toolset()
    
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)

    content = types.Content(role="user", parts=[types.Part(text=prompt)])
    
    final_response_text = "Agent did not produce a final response."

    try:
        async for event in runner.run_async(
            user_id=USER_ID, session_id=SESSION_ID, new_message=content
        ):
            if event.is_final_response() and event.content:
                final_response_text = " ".join(
                    p.text for p in event.content.parts if hasattr(p, 'text') and p.text
                ).strip()
    except Exception as e:
        print(f"ERROR during agent run: {e}")
        final_response_text = f"An error occurred: {e}"
    finally:
        if toolset:
            await toolset.close()
            print("MCP connection closed.")
    
    return final_response_text
