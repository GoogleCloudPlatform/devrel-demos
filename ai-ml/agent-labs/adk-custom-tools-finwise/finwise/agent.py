import os
import sys
import yfinance as yf
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import agent_tool
from google.adk.code_executors import BuiltInCodeExecutor
from mcp import StdioServerParameters
import time
from typing import Dict
from dotenv import load_dotenv
from google.adk.tools.tool_context import ToolContext

# ADK Auth imports
from google.adk.auth import (
    AuthConfig,
    AuthCredential,
    AuthCredentialTypes,
    OAuth2Auth,
)
from fastapi.openapi.models import OAuth2, OAuthFlowAuthorizationCode, OAuthFlows


load_dotenv()

MODEL = os.getenv("MODEL", "gemini-2.0-flash")
MCP_MONTE_CARLO = os.getenv("MCP_MONTE_CARLO")
# The below are demo values; replace with your broker's OAuth2 details if available. This is for the execute_trade tool only.
OAUTH_AUTH_URL = os.getenv("TRADE_OAUTH_AUTH_URL", "https://broker.example.com/oauth/authorize")
OAUTH_TOKEN_URL = os.getenv("TRADE_OAUTH_TOKEN_URL", "https://broker.example.com/oauth/token")
OAUTH_CLIENT_ID = os.getenv("TRADE_OAUTH_CLIENT_ID", "DEMO_CLIENT_ID")
OAUTH_CLIENT_SECRET = os.getenv("TRADE_OAUTH_CLIENT_SECRET", "DEMO_CLIENT_SECRET")
OAUTH_SCOPES = os.getenv("TRADE_OAUTH_SCOPES", "read:portfolio,write:orders")
SCOPES = [s.strip() for s in OAUTH_SCOPES.split(",") if s.strip()]
TOKEN_CACHE_KEY = "trade_oauth_tokens"

def get_stock_price(ticker: str) -> dict:
    """
    Quick path using Yahoo Finance via yfinance.
    Note: quotes are typically delayed 15–20 minutes.
    """
    t = ticker.upper().strip()
    try:
        y = yf.Ticker(t)
        # Try fast path first, then fallbacks
        price = getattr(y.fast_info, "last_price", None) or y.info.get("regularMarketPrice")
        if price is None:
            hist = y.history(period="1d")
            price = float(hist["Close"].iloc[-1]) if not hist.empty else None

        if price is None:
            return {"status": "error", "message": f"No price available for {t}"}

        currency = getattr(y.fast_info, "currency", None) or y.info.get("currency", "USD")
        return {
            "status": "ok",
            "ticker": t,
            "price": float(price),
            "currency": currency,
            "source": "yfinance (delayed)",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

coding_agent = Agent(
    name="CodeAgent",
    model=MODEL,
    instruction=(
        "You can write and run Python for open-ended financial analysis on small, "
        "user-provided data (pandas/numpy/matplotlib available). "
        "Only use code when needed, then end with 'Summary:' and a short explanation."
    ),
    code_executor=BuiltInCodeExecutor(),
)

server_params = StdioServerParameters(
    command=sys.executable,                # str
    args=[MCP_MONTE_CARLO],                # List[str] (must be a list)
    env={"PYTHONUNBUFFERED": "1"},         # Dict[str, str]
    # cwd=os.path.dirname(MCP_MONTE_CARLO) # (optional) working dir
)

monte_carlo_mcp = MCPToolset(
    connection_params=StdioConnectionParams(server_params=server_params)
)


# OAuth2 scheme the ADK client will use to show the consent UI
auth_scheme = OAuth2(
    flows=OAuthFlows(
        authorizationCode=OAuthFlowAuthorizationCode(
            authorizationUrl=OAUTH_AUTH_URL,
            tokenUrl=OAUTH_TOKEN_URL,
            scopes={scope: scope for scope in SCOPES},
        )
    )
)

# Initial credential (client app metadata); ADK uses this to run the auth code flow
auth_credential = AuthCredential(
    auth_type=AuthCredentialTypes.OAUTH2,
    oauth2=OAuth2Auth(
        client_id=OAUTH_CLIENT_ID,
        client_secret=OAUTH_CLIENT_SECRET,
        scopes=SCOPES,
    ),
)

def execute_trade(
    tool_context: ToolContext,
    ticker: str,
    side: str,        # "buy" | "sell"
    quantity: float,
    confirm: bool = False
) -> Dict:
    """
    Execute trade tool that does the following:
      1) Validate params
      2) Ask for confirm=True before doing anything sensitive
      3) If confirmed, acquire tokens using ADK Auth (request_credential / get_auth_response)
      4) Simulate an order (no network calls); return a fake trade_id

    You can plug in your real brokerage by:
      - setting the OAuth ENV vars
      - replacing the simulated section with a requests call
    """
    t = (ticker or "").upper().strip()
    s = (side or "").lower().strip()

    # Basic input validation (keep it simple and JSON-friendly)
    if s not in ("buy", "sell"):
        return {"status": "error", "message": "side must be 'buy' or 'sell'."}
    if not t:
        return {"status": "error", "message": "ticker is required."}
    if quantity <= 0:
        return {"status": "error", "message": "quantity must be > 0."}

    # Ask for explicit confirmation before starting auth
    if not confirm:
        return {
            "status": "needs_confirmation",
            "summary": f"Ready to {s} {quantity} share(s) of {t}. Re-run with confirm=true to proceed.",
            "params": {"ticker": t, "side": s, "quantity": quantity, "confirm": True},
        }

    # Build an AuthConfig for this tool call
    auth_config = AuthConfig(auth_scheme=auth_scheme, raw_auth_credential=auth_credential)

    # Simple session cache (ToolContext.state is a dict persisted by ADK)
    cached = tool_context.state.get(TOKEN_CACHE_KEY)
    access_token = cached.get("access_token") if isinstance(cached, dict) else None

    # If no cached token, see if ADK already exchanged one this turn
    if not access_token:
        exchanged = tool_context.get_auth_response(auth_config)
        if exchanged and exchanged.oauth2 and exchanged.oauth2.access_token:
            access_token = exchanged.oauth2.access_token
            tool_context.state[TOKEN_CACHE_KEY] = {
                "access_token": exchanged.oauth2.access_token,
                "refresh_token": exchanged.oauth2.refresh_token,
            }

    # If still no token, trigger the interactive consent flow and return
    if not access_token:
        tool_context.request_credential(auth_config)
        return {
            "status": "pending_auth",
            "message": "Authentication required. Please complete the sign-in/consent flow.",
        }

    # ----------------------------------------------------------------------
    # ✅ At this point you have an access token.
    # 🔒 This sample app does NOT hit any live API
    #
    # To integrate a real brokerage later:
    #   import requests
    #   resp = requests.post("https://broker/api/orders",
    #                        headers={"Authorization": f"Bearer {access_token}"},
    #                        json={"symbol": t, "side": s, "qty": quantity})
    #   return resp.json()
    # ----------------------------------------------------------------------

    trade_id = f"demo-{int(time.time())}"
    return {
        "status": "ok",
        "trade_id": trade_id,
        "executed": {"ticker": t, "side": s, "quantity": quantity},
        "note": "Demo trade executed locally. No real order was sent.",
    }


root_agent = Agent(
    name="StockStarter",
    model=MODEL,
    description="Minimal ADK app: price tool + (optional) code-exec + Monte Carlo via MCP.",
    instruction=(
        "If the user asks for a stock price, call get_stock_price(ticker). "
        "If they ask for open-ended analysis/plots, call CodeAgent via its tool. "
        "If they ask for a risk simulation/Monte Carlo, call the MCP tool named 'run_monte_carlo' "
        "with sensible defaults (e.g., days=252, trials=1000); summarize key percentiles."
    ),
    tools=[get_stock_price,
           agent_tool.AgentTool(agent=coding_agent),
           monte_carlo_mcp,
           execute_trade
           ],
    
)
