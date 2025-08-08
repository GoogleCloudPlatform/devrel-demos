import asyncio
import json
import sys # Import sys to access stderr
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import yfinance as yf
from scipy.optimize import minimize
from pydantic import BaseModel, Field

# MCP Server Imports
from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# ADK Tool Imports
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

load_dotenv()

# --- Portfolio Optimization Logic ---

def get_historical_data(stocks: list[str], period: str = "1y") -> pd.DataFrame:
    """Downloads historical stock data."""
    # Use 'Close' instead of 'Adj Close' for robustness and disable progress bar.
    data = yf.download(stocks, period=period, progress=False)['Close']
    if data.empty:
        raise ValueError("Could not download historical data for the given stocks.")
    return data

class PortfolioOptimizerInput(BaseModel):
    stocks: list[str] = Field(description="A list of stock ticker symbols.")
    risk_profile: str = Field(description="The user's risk profile (e.g., 'aggressive', 'moderate', 'conservative').")

def run_portfolio_optimization(stocks: list[str], risk_profile: str) -> dict:
    """
    The main function to orchestrate portfolio optimization.
    It downloads historical data, runs a simulation, and returns the optimal allocation.
    """
    data = get_historical_data(stocks)
    
    risk_free_rates = {'aggressive': 0.02, 'moderate': 0.01, 'conservative': 0.005}
    risk_free_rate = risk_free_rates.get(risk_profile.lower(), 0.01)

    returns = data.pct_change().dropna()
    
    def objective(weights):
        portfolio_return = np.sum(returns.mean() * weights) * 252
        portfolio_stddev = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
        sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_stddev
        return -sharpe_ratio

    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bounds = tuple((0, 1) for _ in range(len(stocks)))
    initial_weights = np.array([1./len(stocks)]*len(stocks))

    result = minimize(objective, initial_weights, method='SLSQP', bounds=bounds, constraints=constraints)
    optimal_weights = result.x

    optimized_return = np.sum(returns.mean() * optimal_weights) * 252
    optimized_volatility = np.sqrt(np.dot(optimal_weights.T, np.dot(returns.cov() * 252, optimal_weights)))
    
    return {
        "optimized_allocation": {stock: weight for stock, weight in zip(stocks, optimal_weights)},
        "expected_return": optimized_return,
        "expected_volatility": optimized_volatility
    }

# --- Prepare the ADK Tool ---
print("Initializing ADK portfolio_optimizer tool...", file=sys.stderr)
# Correctly wrap the function in a FunctionTool instance
portfolio_optimizer_tool = FunctionTool(run_portfolio_optimization)
print(f"ADK tool '{portfolio_optimizer_tool.name}' initialized.", file=sys.stderr)


# --- MCP Server Setup ---
print("Creating MCP Server instance...", file=sys.stderr)
app = Server("portfolio-optimizer-mcp-server")

@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """MCP handler to list tools this server exposes."""
    print("MCP Server: Received list_tools request.", file=sys.stderr)
    # Pass the FunctionTool instance to the conversion utility
    mcp_tool_schema = adk_to_mcp_tool_type(portfolio_optimizer_tool)
    print(f"MCP Server: Advertising tool: {mcp_tool_schema.name}", file=sys.stderr)
    return [mcp_tool_schema]

@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    """MCP handler to execute a tool call."""
    print(f"MCP Server: Received call_tool request for '{name}' with args: {arguments}", file=sys.stderr)

    if name == portfolio_optimizer_tool.name:
        try:
            # Await the tool's run_async method
            adk_tool_response = await portfolio_optimizer_tool.run_async(
                args=arguments, tool_context=None
            )
            print(f"MCP Server: ADK tool '{name}' executed.", file=sys.stderr)
            response_text = json.dumps(adk_tool_response, indent=2)
            return [mcp_types.TextContent(type="text", text=response_text)]
        except Exception as e:
            print(f"MCP Server: Error executing ADK tool '{name}': {e}", file=sys.stderr)
            error_text = json.dumps({"error": f"Failed to execute tool '{name}': {str(e)}"})
            return [mcp_types.TextContent(type="text", text=error_text)]
    else:
        print(f"MCP Server: Tool '{name}' not found.", file=sys.stderr)
        error_text = json.dumps({"error": f"Tool '{name}' not implemented by this server."})
        return [mcp_types.TextContent(type="text", text=error_text)]

# --- MCP Server Runner ---
async def run_mcp_stdio_server():
    """Runs the MCP server over standard input/output."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        print("MCP Stdio Server: Starting handshake...", file=sys.stderr)
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
        print("MCP Stdio Server: Run loop finished.", file=sys.stderr)

if __name__ == "__main__":
    print("--- Portfolio Optimizer MCP Server ---", file=sys.stderr)
    print("Attempting to launch...", file=sys.stderr)
    try:
        asyncio.run(run_mcp_stdio_server())
    except KeyboardInterrupt:
        print("\nMCP Server stopped by user.", file=sys.stderr)
    except Exception as e:
        print(f"MCP Server encountered an error: {e}", file=sys.stderr)
    finally:
        print("MCP Server process exiting.", file=sys.stderr)
