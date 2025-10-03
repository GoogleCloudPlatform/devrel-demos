# Finwise ADK Agent
Author: [Smitha Kolan](https://www.linkedin.com/in/smithakolan/)

Finwise — ADK Starter (4 tools). 
This project contains a financial analysis agent built using the Agent Development Kit (ADK).

A minimal Google ADK sample that shows how to build an agent with four tool patterns:

* Function Tool – get_stock_price using yfinance
* Built-in Code Execution – separate CodeAgent for open-ended Python analysis
* MCP Toolset – a Monte Carlo simulation exposed via a tiny MCP stdio server
* Auth (OAuth2) Function Tool – execute_trade (with real auth flow scaffold)

This is designed for devs to extend, keep, swap, or replace tools as you grow.

## Resources

Here are some useful links for the Google Agent Development Kit (ADK):

*   [Google ADK Documentation](https://google.github.io/adk-docs/)
*   [ADK Tools](https://google.github.io/adk-docs/tools/)
*   [Function Tools](https://google.github.io/adk-docs/tools/function-tools/)
*   [Built-in Tools](https://google.github.io/adk-docs/tools/built-in-tools/)
*   [MCP Tools](https://google.github.io/adk-docs/tools/mcp-tools/)
*   [Authentication](https://google.github.io/adk-docs/tools/authentication/)


## Setup
1. Download the `adk-custom-tools-finwise` folder.
2.  **Create a virtual environment:**

    ```bash
    # Go to the finwise folder
    cd adk-custom-tools-finwise/finwise
    ```
3.  **Enter you API key and details**
    Create the .env file within the finwise projecgt folder

    ```bash
    finwise/.env <<'EOF'
    # Model (configure per your environment)
    MODEL=gemini-2.0-flash
    # The agent uses a Google API key for its functionality. You need to set this as an environment variable. You can find in in Google AI Studio: https://aistudio.google.com/app/apikey
    GOOGLE_API_KEY=GOOGLE_API_KEY

    # The mcp server we will make use of is in adk-custom-tools-finwise/mcp-server/monte_carlo_mcp_server.py. You need to provide the absolute path for the file         monte_carlo_mcp_server.py and paste it below.
    MCP_MONTE_CARLO = "[ENTER ABSOLTE PATH to monte_carlo_mcp_server.py]"
    
    # OAuth2 for your execute_trade tool to work. This requires details for brokerage integration — replace with your own details. You can leave the OAuth2 section as-is if you don't want to test execute_trade. The agent will still run
    TRADE_OAUTH_AUTH_URL=https://broker.example.com/oauth/authorize
    TRADE_OAUTH_TOKEN_URL=https://broker.example.com/oauth/token
    TRADE_OAUTH_CLIENT_ID=YOUR_CLIENT_ID
    TRADE_OAUTH_CLIENT_SECRET=YOUR_CLIENT_SECRET
    TRADE_OAUTH_SCOPES=read:portfolio,write:orders
    EOF
    ```
4.  **Create virtual env and install dependencies:**
    ```bash
    # 1) create & activate a virtualenv
    python -m venv .venv
    source .venv/bin/activate                # Windows: .venv\Scripts\activate
    
    # 2) install app deps
    pip install -r requirements.txt

    ```

## Running the Application


1.  **Run the agent using ADK web ui**

    ```bash
    adk web
    ```

2.  **Access the application:**

    Open your web browser and go to:

    [http://127.0.0.1:8000](http://127.0.0.1:8000)

    You can interact with the agent through the web interface provided.

What’s included
1) get_stock_price (Function Tool)

- Minimal placeholder returning a demo price.
- Replace the body with your provider (e.g., yfinance, Polygon, Finnhub).
- Signature kept simple: def get_stock_price(ticker: str) -> dict for clean auto-calling.

2) CodeAgent (Built-in Code Execution)

- Separate agent with BuiltInCodeExecutor for Python analysis (pandas/numpy/matplotlib).
- Exposed to the root via AgentTool (built-ins cannot be combined with other tools on the same agent).

3) Monte Carlo (MCP Toolset)

An external MCP stdio server (monte_carlo_mcp_server.py) that exposes one tool:
- run_monte_carlo(start_price, days, trials, annual_drift, annual_vol, time_budget_s)
- Time-bounded (defaults to 5s) so demos stay snappy.
- ADK spawns the server automatically via STDIO (you do not pre-run it).

4) execute_trade (OAuth2 demo)

- Shows the ADK authentication pattern with ToolContext.request_credential(...) /
get_auth_response(...).
- No real orders are sent; returns a fake trade_id.
- ENV-driven OAuth values so developers can drop in their own provider later.

Test it (copy/paste)
End-to-end (all four tools)
End-to-end tool check. Do these in order:

1) PRICE (get_stock_price):
   - Fetch the price for AAPL and report the number you used.

2) CODE ANALYSIS (use the CodeAgent with built-in code execution):
   - Analyze this tiny CSV. Compute daily returns, then report mean and std.
   CSV:
   date,close
   2025-08-12,100.0
   2025-08-13,101.2
   2025-08-14,100.8
   2025-08-15,102.5
   2025-08-18,103.0
   2025-08-19,102.2
   2025-08-20,103.7
   2025-08-21,104.1
   2025-08-22,103.5
   2025-08-25,104.9
   2025-08-26,105.3
   2025-08-27,106.0

3) MONTE CARLO (MCP run_monte_carlo):
   - Use start_price = the AAPL price you fetched above.
   - days=252, trials=8000, annual_drift=0.07, annual_vol=0.20, time_budget_s=5
   - Return mean/median/p5/p95 of total return %.

4) TRADE (execute_trade):
   - Place a demo BUY for 1 share of AAPL with confirm=true.
   - If authentication is required, trigger the auth flow and proceed.
   - Return the final trade status and trade_id.

Finish with a short summary of what each tool did.

Two-step trade (show confirmation/auth)

Step 1 (no confirm):

Prepare to buy 1 share of AAPL with execute_trade but DO NOT confirm yet.
I want to see the needs_confirmation response and any auth request.


Step 2 (confirm):

execute_trade for AAPL, side=buy, quantity=1, confirm=true.

Monte Carlo time budget stress
Run Monte Carlo with start_price 100, days 252, trials 200000, annual_drift 0.07, annual_vol 0.20, time_budget_s 5.
Return meta.trials_completed and the summary.

