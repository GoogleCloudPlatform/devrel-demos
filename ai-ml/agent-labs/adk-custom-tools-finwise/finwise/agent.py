import os
import math
import random
import statistics
import logging
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams

import requests

load_dotenv()
MODEL = os.getenv("MODEL", "gemini-2.0-flash")

# --- Helper math ------------------------------------------------------------
def _pct_returns(prices: List[float]) -> List[float]:
    return [(prices[i] / prices[i-1] - 1.0) for i in range(1, len(prices))] if len(prices) > 1 else []

def _sharpe(returns: List[float], rf: float = 0.0) -> Optional[float]:
    if not returns:
        return None
    mean = statistics.fmean(returns) - rf
    std = statistics.pstdev(returns) or 1e-12
    return (mean / std) * math.sqrt(252)

def _max_drawdown(prices: List[float]) -> Optional[float]:
    if not prices:
        return None
    peak, max_dd = prices[0], 0.0
    for p in prices:
        peak = max(peak, p)
        max_dd = min(max_dd, (p - peak) / peak)
    return max_dd

def _var(returns: List[float], level: float = 0.95) -> Optional[float]:
    if not returns:
        return None
    sorted_r = sorted(returns)
    idx = max(0, min(len(sorted_r) - 1, int((1 - level) * len(sorted_r))))
    return sorted_r[idx]

def _combine_prices(price_hist: Dict[str, List[float]], weights: Dict[str, float]) -> List[float]:
    if not price_hist:
        return []
    bases = {s: (series[0] or 1.0) for s, series in price_hist.items() if series}
    length = min(len(series) for series in price_hist.values())
    idx = []
    for t in range(length):
        val = 0.0
        for s, series in price_hist.items():
            val += weights.get(s, 0.0) * (series[t] / bases[s]) * 100.0
        idx.append(val)
    return idx

# --- Tool 1: fetch_price_history (Function Tool) ----------------------------
def fetch_price_history(symbols: List[str], days: int = 60, *, state=None) -> dict:
    """
    Demo price generator (replace with your provider or BigQuery).
    Returns dict[symbol]->list[price].
    """
    random.seed(42)
    data: Dict[str, List[float]] = {}
    for s in symbols:
        start = 100.0 + random.random() * 50.0
        series = [start]
        for _ in range(days - 1):
            drift, vol = 0.0005, 0.02
            shock = random.gauss(drift, vol)
            series.append(max(1.0, series[-1] * (1.0 + shock)))
        data[s] = series
    if state is not None:
        state["PRICE_HISTORY"] = data
    logging.info(f"[fetch_price_history] {symbols=} {days=}")
    return {"status": "ok", "symbols": symbols, "days": days}

# --- Tool 2: compute_portfolio_metrics (Function Tool) ----------------------
def compute_portfolio_metrics(weights: Optional[Dict[str, float]] = None,
                              var_level: float = 0.95, *, state=None) -> dict:
    """
    Computes per-asset and portfolio Sharpe / MaxDD / VaR using PRICE_HISTORY in state.
    """
    price_hist: Dict[str, List[float]] = (state or {}).get("PRICE_HISTORY", {})
    if not price_hist:
        return {"status": "error", "message": "PRICE_HISTORY missing. Run fetch_price_history first."}

    symbols = list(price_hist.keys())
    n = len(symbols) or 1
    weights = weights or {s: 1.0 / n for s in symbols}

    per_asset, weighted_daily = {}, None
    for s, series in price_hist.items():
        rets = _pct_returns(series)
        per_asset[s] = {
            "sharpe": _sharpe(rets),
            "max_drawdown": _max_drawdown(series),
            "var": _var(rets, level=var_level),
        }
        w = weights.get(s, 0.0)
        weighted_daily = [w * r for r in rets] if weighted_daily is None \
                         else [a + w*b for a, b in zip(weighted_daily, rets)]

    portfolio = {
        "sharpe": _sharpe(weighted_daily or []),
        "max_drawdown": _max_drawdown(_combine_prices(price_hist, weights)),
        "var": _var(weighted_daily or [], level=var_level),
    }
    result = {"status": "ok", "per_asset": per_asset, "portfolio": portfolio,
              "weights": weights, "var_level": var_level}
    if state is not None:
        state["METRICS"] = result
    logging.info("[compute_portfolio_metrics] done")
    return result

# --- Tool 3: get_stock_price (Function Tool) --------------------------------
def get_stock_price(ticker: str) -> dict:
    """
    Minimal last price (stub). Swap in yfinance/Polygon/etc.
    """
    # For demo, echo back a fake price:
    return {"status": "success", "ticker": ticker, "price": 123.45}

# --- Tool 4: place_market_buy_order (Auth-backed Function Tool) -------------
BROKER_API_URL = os.getenv("BROKER_API_URL")        # e.g. https://broker/api/orders
BROKER_API_TOKEN = os.getenv("BROKER_API_TOKEN")    # Bearer token (kept out of prompts)

def place_market_buy_order(symbol: str, quantity: float) -> dict:
    """
    Places a market buy order via REST with Bearer token from env. Returns API response.
    """
    if not BROKER_API_URL or not BROKER_API_TOKEN:
        return {"status": "error", "message": "Broker API not configured."}
    try:
        resp = requests.post(
            BROKER_API_URL,
            json={"symbol": symbol, "side": "buy", "type": "market", "quantity": quantity},
            headers={"Authorization": f"Bearer {BROKER_API_TOKEN}",
                     "Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        return {"status": "ok", "order": resp.json()}
    except Exception as e:
        logging.exception("trade error")
        return {"status": "error", "message": str(e)}

# --- MCP Toolset: portfolio optimizer (remote) ------------------------------
# Spawns your MCP server as a subprocess via stdio when the agent starts.
optimizer_mcp = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params={
            "command": "python",
            "args": ["-m", "finwise.services.portfolio_optimizer_service"],
        }
    )
)

# --- Root Agent for ADK Web -------------------------------------------------
root_agent = Agent(
    name="Finwise",
    model=MODEL,
    description="Analyze, optimize, price, and (optionally) buy.",
    instruction="""
You are Finwise. Work step-by-step:

1) If symbols/days provided, call fetch_price_history.
2) Compute risk metrics via compute_portfolio_metrics.
3) If asked to optimize, call the MCP optimizer tool (e.g., run_portfolio_optimization).
4) If a specific ticker is requested, call get_stock_price.
5) Only place_market_buy_order when the user clearly confirms symbol + quantity.
Always summarize results clearly before asking for confirmation to trade.
""",
    tools=[
        fetch_price_history,
        compute_portfolio_metrics,
        get_stock_price,
        place_market_buy_order,
        optimizer_mcp,
    ],
)
