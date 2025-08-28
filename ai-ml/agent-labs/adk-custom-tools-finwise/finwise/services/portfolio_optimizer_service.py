# finwise/services/portfolio_optimizer_service.py
"""
MCP server exposing a single tool: run_portfolio_optimization(stocks, risk_profile, period="1y")

- Fetches historical prices (yfinance). Falls back to synthetic data if download fails.
- Computes daily returns; annualizes mean and covariance.
- Maximizes Sharpe ratio via SciPy SLSQP. Falls back to equal-weights if SciPy unavailable.

Start:  python -m finwise.services.portfolio_optimizer_service
ADK connects via StdioConnectionParams (see agent wiring).
"""

import asyncio
import json
import math
import random
import sys
from typing import List, Dict

# ---------------- deps (optional fallbacks) ----------------
try:
    import pandas as pd
    import numpy as np
except Exception as _e:
    print(f"[warn] pandas/numpy not available: {_e}", file=sys.stderr)
    pd = None
    np = None

try:
    import yfinance as yf
except Exception as _e:
    print(f"[warn] yfinance not available: {_e}", file=sys.stderr)
    yf = None

try:
    from scipy.optimize import minimize
except Exception as _e:
    print(f"[warn] scipy not available: {_e}", file=sys.stderr)
    minimize = None

# ---------------- MCP server primitives -------------------
from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# ---------------- ADK bridge ------------------------------
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type


# ====== Core logic ==========================================================

def _synthetic_prices(days: int = 252) -> List[float]:
    """Geometric-random-walk synthetic price series."""
    random.seed(7)
    start = 100.0 + random.random() * 30.0
    series = [start]
    for _ in range(days - 1):
        drift, vol = 0.0004, 0.018
        shock = random.gauss(drift, vol)
        series.append(max(1.0, series[-1] * (1.0 + shock)))
    return series

def _download_prices(stocks: List[str], period: str):
    """Returns DataFrame of Close prices [date x ticker]. Falls back to synthetic."""
    if pd is None:
        # No pandas: produce a minimal dict of lists
        return {s: _synthetic_prices() for s in stocks}

    if yf is None:
        return pd.DataFrame({s: _synthetic_prices() for s in stocks})

    try:
        data = yf.download(stocks, period=period, progress=False)["Close"]
        # Normalize to a 2D frame regardless of single/multi ticker
        if isinstance(data, pd.Series):
            data = data.to_frame(name=stocks[0])
        if data.empty:
            raise ValueError("Empty Yahoo response")
        return data
    except Exception as e:
        print(f"[warn] yfinance failed ({e}); using synthetic data.", file=sys.stderr)
        return pd.DataFrame({s: _synthetic_prices() for s in stocks})

def _to_numpy_frame(frame_or_dict):
    """Ensures we have numpy arrays for math, plus tickers list."""
    if pd is None or isinstance(frame_or_dict, dict):
        # dict[str, list]
        tickers = list(frame_or_dict.keys())
        mat = []
        length = min(len(v) for v in frame_or_dict.values())
        for t in range(length):
            mat.append([frame_or_dict[s][t] for s in tickers])
        return tickers, np.array(mat, dtype=float) if np else None
    else:
        tickers = list(frame_or_dict.columns)
        return tickers, frame_or_dict.to_numpy(dtype=float)

def _daily_returns(price_matrix):
    return (price_matrix[1:] / price_matrix[:-1]) - 1.0

def _annualized_mean_cov(returns):
    mean = returns.mean(axis=0) * 252.0
    cov = np.cov(returns.T) * 252.0
    return mean, cov

def _optimize_sharpe(mean, cov, rf=0.01):
    n = mean.shape[0]
    w0 = np.ones(n) / n
    bounds = [(0.0, 1.0)] * n

    def neg_sharpe(w):
        ret = float(w @ mean)
        vol = float(math.sqrt(max(w @ cov @ w, 1e-12)))
        return -((ret - rf) / vol)

    cons = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    if minimize is None:
        # Fallback: equal weights
        return w0
    res = minimize(neg_sharpe, w0, method="SLSQP", bounds=bounds, constraints=cons)
    return res.x if res.success else w0


# ====== ADK tool function ===================================================

def run_portfolio_optimization(stocks: List[str], risk_profile: str, period: str = "1y") -> dict:
    """
    Inputs:
      - stocks: list of tickers
      - risk_profile: 'aggressive' | 'moderate' | 'conservative' (sets RF)
      - period: yfinance period string (e.g., '6mo', '1y', '2y')
    Output:
      {
        optimized_allocation: {ticker: weight},
        expected_return: float (annualized),
        expected_volatility: float (annualized std),
        sharpe: float
      }
    """
    if not stocks:
        return {"status": "error", "message": "Provide at least one stock symbol."}

    rf_map = {"aggressive": 0.02, "moderate": 0.01, "conservative": 0.005}
    rf = rf_map.get(risk_profile.lower(), 0.01)

    prices = _download_prices(stocks, period)
    tickers, mat = _to_numpy_frame(prices)
    if np is None or mat is None:
        # No numpy: trivial equal-weights return
        alloc = {s: 1.0 / len(tickers) for s in tickers}
        return {
            "status": "ok",
            "optimized_allocation": alloc,
            "expected_return": None,
            "expected_volatility": None,
            "sharpe": None,
            "note": "numpy/scipy unavailable; returned equal weights."
        }

    rets = _daily_returns(mat)
    mean, cov = _annualized_mean_cov(rets)
    w = _optimize_sharpe(mean, cov, rf=rf)

    port_ret = float(w @ mean)
    port_vol = float(math.sqrt(max(w @ cov @ w, 1e-12)))
    sharpe = (port_ret - rf) / (port_vol or 1e-12)

    return {
        "status": "ok",
        "optimized_allocation": {t: float(wi) for t, wi in zip(tickers, w)},
        "expected_return": port_ret,
        "expected_volatility": port_vol,
        "sharpe": sharpe,
        "risk_free_rate": rf,
        "period": period,
    }


# ====== Wrap as ADK FunctionTool and expose via MCP =========================

portfolio_optimizer_tool = FunctionTool(run_portfolio_optimization)

app = Server("finwise-portfolio-optimizer-mcp")

@app.list_tools()
async def list_mcp_tools() -> List[mcp_types.Tool]:
    # Convert the ADK FunctionTool into an MCP Tool schema
    tool_schema = adk_to_mcp_tool_type(portfolio_optimizer_tool)
    return [tool_schema]

@app.call_tool()
async def call_mcp_tool(name: str, arguments: Dict) -> List[mcp_types.Content]:
    if name != portfolio_optimizer_tool.name:
        return [mcp_types.TextContent(type="text", text=json.dumps({"error": f"unknown tool {name}"}))]
    try:
        result = await portfolio_optimizer_tool.run_async(args=arguments, tool_context=None)
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        err = {"error": f"execution failed: {e}"}
        print(err, file=sys.stderr)
        return [mcp_types.TextContent(type="text", text=json.dumps(err))]

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
    try:
        asyncio.run(run_mcp_stdio_server())
    except KeyboardInterrupt:
        pass
