#!/usr/bin/env python3
"""
MCP server exposing an ADK FunctionTool: run_monte_carlo

Pattern:
- Implement a plain Python function (JSON-friendly args/return)
- Wrap it with google.adk.tools.function_tool.FunctionTool
- Convert ADK tool schema -> MCP tool schema via adk_to_mcp_tool_type
- Implement @app.list_tools and @app.call_tool
- Run over STDIO (no prints to stdout before handshake)
"""

import asyncio, json, math, random, sys
from time import perf_counter
from typing import Dict

# --- MCP server (low-level, stdio) ---
from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# --- ADK tool wrapper + schema conversion ---
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type


# ─────────────────────────────────────────────────────────────────────────────
# ADK Function Tool: time-bounded Monte Carlo simulation
# ─────────────────────────────────────────────────────────────────────────────
def run_monte_carlo(
    start_price: float,
    days: int = 252,
    trials: int = 10000,         # user may request more; capped by time budget
    annual_drift: float = 0.07,
    annual_vol: float = 0.20,
    time_budget_s: float = 5.0,  # hard ceiling for responsiveness
) -> Dict:
    """
    Time-bounded Monte Carlo using discrete GBM-like compounding.
    Uses NumPy if available; falls back to pure-Python.
    Returns summary stats and how many trials actually ran.
    """
    if start_price <= 0 or days <= 0 or trials <= 0:
        return {"status": "error", "message": "Invalid inputs."}

    mu_d = annual_drift / 252.0
    sigma_d = annual_vol / (252.0 ** 0.5)

    # Try fast vectorized engine
    use_numpy = False
    rng = None
    try:
        import numpy as np  # lazy import keeps server startup fast
        rng = np.random.default_rng()
        use_numpy = True
    except Exception:
        use_numpy = False

    t0 = perf_counter()
    ends = []
    trials_done = 0
    batch = 20000 if use_numpy else 200  # adjust if you want larger/smaller chunks

    def time_left() -> float:
        return time_budget_s - (perf_counter() - t0)

    while trials_done < trials and time_left() > 0.1:
        remaining = trials - trials_done
        b = min(batch, remaining)

        if use_numpy:
            import numpy as np
            r = rng.normal(loc=mu_d, scale=sigma_d, size=(b, days))
            chunk = (start_price * (1.0 + r).prod(axis=1)).tolist()
        else:
            chunk = []
            for _ in range(b):
                p = start_price
                for _ in range(days):
                    p *= (1.0 + random.gauss(mu_d, sigma_d))
                chunk.append(p)

        ends.extend(chunk)
        trials_done += b

    # Ensure at least one very quick sample if time was ultra-tight
    if not ends:
        p = start_price
        for _ in range(min(days, 32)):
            p *= (1.0 + random.gauss(mu_d, sigma_d))
        ends = [p]
        trials_done = 1

    ends.sort()
    n = len(ends)
    mean = sum(ends) / n
    median = ends[n // 2]
    p5 = ends[max(0, int(0.05 * n) - 1)]
    p95 = ends[min(n - 1, int(0.95 * n) - 1)]
    to_pct = lambda x: (x / start_price - 1.0) * 100.0
    elapsed = perf_counter() - t0
    truncated = (trials_done < trials)

    return {
        "status": "ok",
        "inputs": {
            "start_price": start_price,
            "days": days,
            "trials_requested": trials,
            "annual_drift": annual_drift,
            "annual_vol": annual_vol,
            "time_budget_s": time_budget_s,
        },
        "summary": {
            "end_price": {"mean": mean, "median": median, "p5": p5, "p95": p95},
            "total_return_pct": {
                "mean": to_pct(mean), "median": to_pct(median),
                "p5": to_pct(p5), "p95": to_pct(p95),
            },
        },
        "meta": {
            "trials_completed": trials_done,
            "elapsed_seconds": elapsed,
            "truncated": truncated,
            "engine": "numpy" if use_numpy else "python",
        },
    }


# Wrap the function as an ADK FunctionTool
monte_carlo_tool = FunctionTool(run_monte_carlo)


# ─────────────────────────────────────────────────────────────────────────────
# MCP server: advertise & execute the wrapped ADK tool
# ─────────────────────────────────────────────────────────────────────────────
app = Server("adk-monte-carlo-mcp")

@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    tool_schema = adk_to_mcp_tool_type(monte_carlo_tool)
    return [tool_schema]

@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    if name != monte_carlo_tool.name:
        err = {"error": f"Tool '{name}' not implemented by this server."}
        return [mcp_types.TextContent(type="text", text=json.dumps(err))]
    try:
        # No ToolContext in this simple server (run outside ADK Runner)
        result = await monte_carlo_tool.run_async(args=arguments, tool_context=None)
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        err = {"error": f"Execution failed: {e}"}
        print(err, file=sys.stderr)  # log to stderr, not stdout
        return [mcp_types.TextContent(type="text", text=json.dumps(err))]


# ─────────────────────────────────────────────────────────────────────────────
# stdio runner
# ─────────────────────────────────────────────────────────────────────────────
async def run_mcp_stdio_server():
    async with mcp.server.stdio.stdio_server() as (r, w):
        await app.run(
            r, w,
            InitializationOptions(
                server_name=app.name,
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    # DO NOT print to stdout before handshake; stderr is fine if you need logs.
    try:
        asyncio.run(run_mcp_stdio_server())
    except KeyboardInterrupt:
        pass
