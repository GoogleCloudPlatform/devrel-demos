# Finwise ADK Agent

## Resources

Here are some useful links for the Google Agent Development Kit (ADK):

*   [Google ADK Documentation](https://google.github.io/adk-docs/)
*   [ADK Tools](https://google.github.io/adk-docs/tools/)
*   [Function Tools](https://google.github.io/adk-docs/tools/function-tools/)
*   [Built-in Tools](https://google.github.io/adk-docs/tools/built-in-tools/)
*   [MCP Tools](https://google.github.io/adk-docs/tools/mcp-tools/)
*   [Authentication](https://google.github.io/adk-docs/tools/authentication/)

This project contains a financial analysis agent built using the Google Agent Development Kit (ADK).

## Agent Workflow

The Finwise agent is designed to follow a strict, sequential workflow to ensure a structured and predictable user experience. The agent's instructions enforce the following order of operations:

1.  **Analyze**: The agent's first step is always to analyze the user's request using the `AnalystAgent`. This specialized agent performs data analysis, generates insights, and can create plots.
2.  **Optimize**: After the analysis is complete, the agent uses the `run_portfolio_optimization` tool to determine the optimal asset allocation based on the user's risk profile.
3.  **Price**: Once the optimal allocation is determined, the agent uses the `get_stock_price` tool to fetch the latest price of the top-recommended stock.
4.  **Confirm and Execute**: Finally, the agent presents the stock price to the user and asks for confirmation before executing a trade using the `execute_trade` tool.

## Tool Descriptions

The Finwise agent utilizes four key tools to perform its financial analysis and trading tasks:

1.  **`AnalystAgent`**: A specialized sub-agent that uses a built-in code executor to perform data analysis, generate insights, and create plots using Python and Matplotlib.
2.  **`PortfolioOptimizer` (MCP Tool)**: A tool that runs in a separate process and is accessed via the Media Control Protocol (MCP). It takes a list of stocks and a risk profile to calculate the optimal investment allocation.
3.  **`get_stock_price`**: A function tool that fetches the most recent stock price for a given ticker symbol using the `yfinance` library.
4.  **`execute_trade`**: A function tool that simulates the execution of a stock trade. It includes a full OAuth 2.0 authentication flow to demonstrate how to handle secure transactions.

## Setup

1.  **Create a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your API key:**

    The agent uses a Google API key for its functionality. You need to set this as an environment variable.

    Create a `.env` file in the root of the project:

    ```
    GOOGLE_API_KEY="YOUR_API_KEY"
    ```

    Replace `"YOUR_API_KEY"` with your actual Google API key. The application will load this key from the `.env` file.

## Running the Application

This project uses a FastAPI server to provide an interface to the Finwise agent.

1.  **Start the server:**

    ```bash
    uvicorn finwise.server:app --reload
    ```

2.  **Access the application:**

    Open your web browser and go to:

    [http://127.0.0.1:8000](http://127.0.0.1:8000)

    You can interact with the agent through the web interface provided.
