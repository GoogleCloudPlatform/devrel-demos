Finwise (ADK Skeleton)
======================

A tiny starter that shows how to build an **ADK** agent with:

*   simple function tools,
    
*   a community **MCP** server for market data (Yahoo Finance) mounted over **STDIO**,
    
*   and the **ADK Web UI** (no custom frontend).
    

1) Download the Financial Data MCP Server
-----------------------------------------

This app expects the **community MCP server** from:

**Repo:** [https://github.com/Samarth2001/Financial-Data-MCP-Server](https://github.com/Samarth2001/Financial-Data-MCP-Server?utm_source=chatgpt.com)

### Download just the file

1.  Open the repo above → click server.py → click **Raw**.
    
2.  Copy the raw URL and download it:
    

**macOS/Linux**

`   mkdir -p external/financial-data-mcp  curl -L "" -o external/financial-data-mcp/server.py   `

**Windows PowerShell**

`   New-Item -ItemType Directory -Force external\financial-data-mcp | Out-Null  Invoke-WebRequest -Uri "" -OutFile "external\financial-data-mcp\server.py"   `

Then set the absolute path in .env:

`   FIN_MCP_SERVER=/absolute/path/to/your/project/external/financial-data-mcp/server.py   `

> **Tip:** use an **absolute** path. Relative paths can break when ADK spawns the process.

2) Install dependencies
-----------------------

Create a virtualenv and install the app deps:
`   python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate  pip install -r finwise/requirements.txt   `

Install the **MCP server** deps in the **same venv** (ADK will spawn this Python):
`   pip install "mcp[cli]" yfinance pandas numpy   `

3) Configure environment
------------------------

Create .env from the example and edit paths/keys:
`   cp finwise/.env.example finwise/.env   `

**finwise/.env**
`   MODEL=gemini-2.0-flash  # If using AI Studio:  # GOOGLE_API_KEY=YOUR_API_KEY  # Absolute path to the community MCP server script you downloaded/cloned  FIN_MCP_SERVER=/absolute/path/to/your/project/external/financial-data-mcp/server.py   `

4) Run the ADK Web UI
---------------------
`   export PYTHONPATH=$PWD   # Windows PowerShell: $env:PYTHONPATH = $PWD  adk web   `

Open the URL the CLI prints, select **Finwise**, and try prompts like:

*   “What’s the current price of AAPL?”
    
*   “Show TSLA’s 50-day moving average.”
    
*   “Compare AAPL, MSFT, and GOOGL performance.”
    
*   “Confirm: buy 1 share of AAPL.”
    

5) (Optional) Sanity-check the MCP server
-----------------------------------------

Verify the server lists tools correctly with the MCP CLI (using **this** Python):
`   mcp list-tools --stdio \    --command "$(python -c 'import sys; print(sys.executable)')" \    --args "/absolute/path/to/.../server.py"   `

You should see tools like: get\_stock\_price, get\_historical\_data, get\_options\_chain, calculate\_moving\_average, calculate\_rsi, calculate\_sharpe\_ratio, compare\_stocks, clear\_cache.

Troubleshooting
---------------

*   **“Timed out while waiting for client response”**The MCP server likely takes too long to start or the path is wrong. Ensure FIN\_MCP\_SERVER is correct and the server’s deps are installed in the same venv.
    
*   **“Connection closed”**Make sure you’re using **STDIO** (StdioConnectionParams), not HTTP. Also avoid any prints to **stdout** before the MCP handshake (logs should go to stderr in the server).
    
*   **Missing data or modules**Install the server deps:pip install "mcp\[cli\]" yfinance pandas numpy
    

