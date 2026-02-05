import os
import shutil
from dotenv import load_dotenv
from mcp import StdioServerParameters
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool import StreamableHTTPConnectionParams, StdioConnectionParams

load_dotenv()

def get_reddit_mcp_toolset():
    """Reddit MCP for engagement analysis."""
    cmd = "reddit-mcp" if shutil.which("reddit-mcp") else "npx"
    args = [] if shutil.which("reddit-mcp") else ["-y", "--quiet", "reddit-mcp"]
    env = {**os.environ, "DOTENV_CONFIG_SILENT": "true", "LANG": "en_US.UTF-8"}
    
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command=cmd, args=args, env=env),
            timeout=120.0
        )
    )

def get_dk_mcp_toolset():
    """DeveloperKnowledge MCP for official GCP docs."""
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="https://developerknowledge.googleapis.com/mcp",
            headers={"X-Goog-Api-Key": os.getenv("DK_API_KEY", "")}
        )
    )

def get_nano_banana_mcp_toolset():
    """Nano Banana MCP for image generation."""
    path = os.path.join("dev_signal_agent", "tools", "nano_banana_mcp", "main.py")
    bucket = os.getenv("AI_ASSETS_BUCKET") or os.getenv("LOGS_BUCKET_NAME")
    env = {
        **os.environ, 
        "MCP_TRANSPORT": "stdio", 
        "DOTENV_CONFIG_SILENT": "true",
        "AI_ASSETS_BUCKET": bucket
    }
    
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command="uv", args=["run", path], env=env),
            timeout=600.0
        )
    )

