import json
from pydantic import BaseModel, Field
from google.adk.tools.function_tool import FunctionTool, ToolContext
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.adk.auth import AuthConfig, AuthCredential, AuthCredentialTypes, OAuth2Auth
from fastapi.openapi.models import OAuth2, OAuthFlowAuthorizationCode, OAuthFlows
import sys


class TradeInput(BaseModel):
    ticker: str = Field(description="The stock ticker symbol.")
    shares: int = Field(description="The number of shares to trade.")
    action: str = Field(description="The trade action, either 'buy' or 'sell'.")

# --- Authentication Configuration ---
TOKEN_CACHE_KEY = "trading_tool_tokens"
SCOPES = ["read:portfolio", "write:orders"]

auth_scheme = OAuth2(
    flows=OAuthFlows(
        authorizationCode=OAuthFlowAuthorizationCode(
            authorizationUrl="https://brokerage.example.com/oauth/authorize",
            tokenUrl="https://brokerage.example.com/oauth/token",
            scopes={scope: "Scope for trading API" for scope in SCOPES},
        )
    )
)
auth_credential = AuthCredential(
    auth_type=AuthCredentialTypes.OAUTH2,
    auth_config=OAuth2Auth(
        client_id="YOUR_DUMMY_CLIENT_ID",
        client_secret="YOUR_DUMMY_CLIENT_SECRET",
        scopes=SCOPES,
    ),
)
# --- End Authentication Configuration ---

def execute_trade_logic(input: TradeInput, tool_context: ToolContext) -> dict:
    """Executes a trade after handling the full authentication flow."""
    creds = None
    
    # Step 1: Check for Cached & Valid Credentials
    if tool_context and tool_context.state:
        cached_token_info = tool_context.state.get(TOKEN_CACHE_KEY)
        if cached_token_info:
            try:
                creds = Credentials.from_authorized_user_info(json.loads(cached_token_info), SCOPES)
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    tool_context.state[TOKEN_CACHE_KEY] = creds.to_json()
                elif not creds.valid:
                    creds = None
            except Exception as e:
                print(f"Error loading/refreshing cached creds: {e}", file=sys.stderr)
                creds = None
    
    # If we have valid credentials, skip to the API call
    if creds and creds.valid:
        pass # Fall through to Step 5
    else:
        # Step 2: Check for Auth Response from Client
        auth_config = AuthConfig(auth_scheme=auth_scheme, raw_auth_credential=auth_credential)
        exchanged_credential = tool_context.get_auth_response(auth_config)
        
        if exchanged_credential and exchanged_credential.oauth2 and exchanged_credential.oauth2.access_token:
            creds = Credentials(
                token=exchanged_credential.oauth2.access_token,
                refresh_token=exchanged_credential.oauth2.refresh_token,
                token_uri=auth_scheme.flows.authorizationCode.tokenUrl,
                client_id=auth_credential.oauth2.client_id,
                client_secret=auth_credential.oauth2.client_secret,
                scopes=SCOPES,
            )
            # Step 5 (early): Cache the newly obtained credentials
            if tool_context.state:
                tool_context.state[TOKEN_CACHE_KEY] = creds.to_json()
        else:
            # Step 3: Initiate Authentication Request
            tool_context.request_credential(auth_config)
            return {"status": "pending_auth", "message": "User authentication is required."}

    # Step 6: Make Authenticated API Call
    if not creds or not creds.valid:
        return {"status": "error", "message": "Authentication failed. Could not obtain valid credentials."}
    
    print(f"DUMMY API CALL: Executing {input.action} for {input.shares} shares of {input.ticker} with a valid token.")
    
    # Step 7: Return Tool Result
    return {"status": "success", "message": f"Trade for {input.shares} shares of {input.ticker} executed successfully."}


execute_trade = FunctionTool(func=execute_trade_logic)
