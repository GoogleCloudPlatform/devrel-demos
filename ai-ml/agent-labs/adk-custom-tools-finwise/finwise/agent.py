import os
import sys
from typing import List, Dict

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams

load_dotenv()

# === Model selection (AI Studio or Vertex configured outside) ===============
MODEL = os.getenv("MODEL", "gemini-2.0-flash")

# === MCP: Community Financial Data Server (STDIO) ===========================
# Point this at the community server script you have (ABSOLUTE PATH recommended).
# Example:
#   FIN_MCP_SERVER=/abs/path/to/server.py
FIN_MCP_SERVER = os.getenv("FIN_MCP_SERVER", "/abs/path/to/financial_data_server.py")

financial_data_mcp = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params={
            "command": sys.executable,       # use current venv's python
            "args": [FIN_MCP_SERVER],        # path to the community server script
            "env": {"PYTHONUNBUFFERED": "1"} # important for stdio streaming
        }
    )
)

# === Tool 1: analyze_request ===============================================
def analyze_request(tool_context: ToolContext,
                    symbols: List[str],
                    risk_profile: str = "moderate") -> Dict:
    """
    Records user's intent (symbols + risk). Keep signatures JSON-simple.
    """
    tool_context.state["symbols"] = symbols
    tool_context.state["risk_profile"] = risk_profile
    return {"status": "ok", "symbols": symbols, "risk_profile": risk_profile}

# === Tool 2: optimize_allocation (stub) =====================================
def optimize_allocation(tool_context: ToolContext) -> Dict:
    """
    Returns equal weights as a placeholder.
    # TODO: replace with real optimizer or mount a separate MCP optimizer later.
    """
    symbols: List[str] = tool_context.state.get("symbols", [])
    if not symbols:
        return {"status": "error", "message": "Run analyze_request first."}
    w = 1.0 / max(1, len(symbols))
    weights = {s: w for s in symbols}
    tool_context.state["weights"] = weights
    return {"status": "ok", "weights": weights}

# === Tool 3: execute_trade (stub) ===========================================
def execute_trade(symbol: str, quantity: float, action: str = "buy") -> Dict:
    """
    Trade stub for demos. Put your real brokerage logic here (OAuth, REST, etc).
    """
    # TODO: implement secure auth + API call to your brokerage here.
    return {"status": "ok", "message": f"trade executed: {action} {quantity} {symbol}"}

# === Root Agent =============================================================
root_agent = Agent(
    name="Finwise",
    model=MODEL,
    description="Starter ADK agent wired to a financial-data MCP server.",
    instruction="""
Follow this sequence, step by step:

1) Analyze — call analyze_request to capture symbols and risk_profile.
2) Optimize — call optimize_allocation (equal weights for now).
3) Price — use the Financial Data MCP tools for market data:
   Prefer these tool names if available:
     - get_stock_price (e.g., {"symbol":"AAPL"})
     - get_historical_data ({"symbol":"MSFT","period":"1y","interval":"1d"})
     - compare_stocks ({"symbols":["AAPL","MSFT","GOOGL"]})
     - calculate_moving_average / calculate_rsi / calculate_sharpe_ratio
     - get_options_chain
   Note: Yahoo prices may be delayed ~15–20 minutes.

4) Confirm & Execute — only call execute_trade after the user clearly confirms
   the symbol and quantity.

Always summarize what you did and what you'll do next.
""",
    tools=[
        analyze_request,
        optimize_allocation,
        financial_data_mcp,  # mounts the community MCP server tools
        execute_trade,
    ],
)
