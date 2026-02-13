import logging
import os
import sys
from fastmcp import FastMCP
from dotenv import load_dotenv
from nano_banana_pro import generate_image

def _initialize_console_logging(min_level: int = logging.INFO):
    # Ensure logs go to STDERR so they don't break the MCP stdio protocol
    handler = logging.StreamHandler(sys.stderr)
    logging.basicConfig(level=min_level, handlers=[handler], force=True)

tools = [generate_image]
mcp = FastMCP(name="MediaGenerators", tools=tools)

if __name__ == "__main__":
    load_dotenv()
    _initialize_console_logging()
    mcp.run(transport="stdio")

