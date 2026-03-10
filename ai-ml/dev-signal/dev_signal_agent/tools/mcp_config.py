import os
import shutil
from mcp import StdioServerParameters
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool import StreamableHTTPConnectionParams, StdioConnectionParams

def get_reddit_mcp_toolset(client_id: str = "", client_secret: str = "", user_agent: str = ""):
    """
    Connects to the Reddit MCP server.
    This server runs as a local subprocess (stdio) and proxies requests to the Reddit API.
    """
    # Check if 'reddit-mcp' is installed globally, otherwise use npx to run it
    cmd = "reddit-mcp" if shutil.which("reddit-mcp") else "npx"
    args = [] if shutil.which("reddit-mcp") else ["-y", "--quiet", "reddit-mcp"]
    
    # Inject secrets into the environment of the subprocess only
    env = {
        **os.environ, 
        "DOTENV_CONFIG_SILENT": "true", 
        "LANG": "en_US.UTF-8"
    }

    if client_id: env["REDDIT_CLIENT_ID"] = client_id
    if client_secret: env["REDDIT_CLIENT_SECRET"] = client_secret
    if user_agent: env["REDDIT_USER_AGENT"] = user_agent

    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=cmd, 
                args=args, 
                env=env # Pass injected secrets directly to the subprocess
            ),
            timeout=120.0
        )
    )

def get_dk_mcp_toolset(api_key: str = ""):
    """
    Connects to Developer Knowledge (Google Cloud Docs).
    This is a remote MCP server accessed via HTTP.
    """
    headers = {}
    if api_key:
        headers["X-Goog-Api-Key"] = api_key
    else:
        # Fallback to os.environ for local testing if not passed via API
        headers["X-Goog-Api-Key"] = os.getenv("DK_API_KEY", "")

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="https://developerknowledge.googleapis.com/mcp",
            headers=headers
        )
    )

def get_nano_banana_mcp_toolset():
    """
    Connects to our local 'Nano Banana' image generator.
    This demonstrates how to wrap a local Python script as an MCP tool.
    """
    path = os.path.join("dev_signal_agent", "tools", "nano_banana_mcp", "main.py")
    bucket = os.getenv("AI_ASSETS_BUCKET") 
    
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="uv", 
                args=["run", path], 
                env={**os.environ, "AI_ASSETS_BUCKET": bucket}
            ),
            timeout=600.0 # Image generation can take time
        )
    )
