import os
import shutil
from mcp import StdioServerParameters
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool import StreamableHTTPConnectionParams, StdioConnectionParams

def get_stdio_mcp_toolset(command: str, args: list, secrets: dict = None):
    """
    Connects to a local MCP server via stdio.
    Suitable for tools like 'reddit-mcp'.
    """
    env = {**os.environ, "DOTENV_CONFIG_SILENT": "true"}
    if secrets:
        env.update(secrets)

    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=command,
                args=args,
                env=env
            ),
            timeout=120.0
        )
    )

def get_http_mcp_toolset(url: str, api_key: str = "", header_name: str = "X-Goog-Api-Key"):
    """
    Connects to a remote MCP server via HTTP.
    Suitable for managed knowledge servers.
    """
    headers = {header_name: api_key} if api_key else {}
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=url,
            headers=headers
        )
    )

def get_uv_run_connector(script_path: str, env_vars: dict = None):
    """
    Connects to a local Python script using 'uv run'.
    """
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="uv",
                args=["run", script_path],
                env={**os.environ, **(env_vars or {})}
            ),
            timeout=600.0
        )
    )
