# Finwise ADK Agent

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
